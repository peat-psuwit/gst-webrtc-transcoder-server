import asyncio
import gi

from typing import Literal, Optional, TYPE_CHECKING

from .gst_util import create_gst_webtrc_sdp
from .types import RawMedia

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstWebRTC

# Ensure that gst-python is installed
try:
    from gi.overrides import Gst as _
except ImportError:
    print("gstreamer-python binding overrides aren't available, please install them")
    raise

# https://www.reddit.com/r/Python/comments/18gsr42/are_there_any_peps_about_type_imports/
if TYPE_CHECKING:
    # pylint: disable = ungrouped-imports
    from .app import App
    from .ws_session import WsSession
else:
    # Type stub
    class App:
        pass

    class WsSession:
        pass


class PlayerSession:
    id: str
    ws_session: Optional[WsSession]
    app: App
    event_loop: asyncio.AbstractEventLoop

    gst_pipe: Gst.Pipeline
    gst_bus: Gst.Bus
    gst_webrtc: Gst.Element
    gst_webrtc_signaller: GObject.Object

    is_making_offer: bool
    expect_video: bool

    def __init__(
        self,
        id: str,
        media_urls: list[RawMedia],
        ws_session: WsSession,
        app: App,
        event_loop: asyncio.AbstractEventLoop,
    ):
        self.id = id
        self.ws_session = ws_session
        self.app = app
        self.event_loop = event_loop
        self.is_making_offer = False
        self.expect_video = False

        for media in media_urls:
            if media.expect_video:
                self.expect_video = True
                break

        Gst.init(None)

        pipeline_string = (
            "webrtcsink name=webrtc "
            "do-fec=false do-retransmission=true "
            # video/x-h265 (x265enc) doesn't support bitrate control.
            # video/x-av1 outright doesn't work for some reason (rtpav1pay complains
            # "Generated packet has bigger size 1208 than MTU 1200").
            # Prefer more modern codecs over older ones.
            "video-caps=video/x-vp9;video/x-vp8;video/x-h264 "
            "start-bitrate=32000 max-bitrate=50000"
        )
        for i, media in enumerate(media_urls):
            pipeline_string += f" uridecodebin3 name=dec{i}"

            if media.expect_video:
                pipeline_string += (
                    f" dec{i}. ! videorate ! videoscale !"
                    f" video/x-raw,height=[1,144],framerate=[1/1,5/1] ! webrtc."
                )

            if media.expect_audio:
                pipeline_string += (
                    f" dec{i}. ! audioconvert !"
                    f" audio/x-raw{',channels=1' if self.expect_video else ''} !"
                    f" webrtc."
                )

        self.gst_pipe = Gst.parse_launch_full(
            pipeline_string,
            None,  # GstParseContext
            Gst.ParseFlags.FATAL_ERRORS,
        )

        self.gst_bus = self.gst_pipe.get_bus()
        self.gst_bus.add_watch(GLib.PRIORITY_DEFAULT, self.bus_on_message)

        for i, media in enumerate(media_urls):
            dec = self.gst_pipe.get_by_name(f"dec{i}")
            dec.props.uri = media_urls[i].url

        self.gst_webrtc = self.gst_pipe.get_by_name("webrtc")
        self.gst_webrtc.connect("encoder-setup", self.on_encoder_setup)

        self.gst_webrtc_signaller = self.gst_webrtc.props.signaller
        self.gst_webrtc_signaller.connect("start", self.signaller_on_start)
        self.gst_webrtc_signaller.connect("stop", self.signaller_on_stop)
        self.gst_webrtc_signaller.connect(
            "send-session-description", self.signaller_on_send_session_description
        )
        self.gst_webrtc_signaller.connect("send-ice", self.signaller_on_send_ice)
        self.gst_webrtc_signaller.connect("end-session", self.signaller_on_end_session)
        self.gst_webrtc_signaller.connect(
            "consumer-added", self.signaller_on_consumer_added
        )
        self.gst_webrtc_signaller.connect(
            "consumer-removed", self.signaller_on_consumer_removed
        )
        try:
            self.gst_webrtc_signaller.connect(
                "webrtcbin-ready", self.signaller_on_webrtcbin_ready
            )
        except TypeError:
            pass

        self.gst_pipe.set_state(Gst.State.PLAYING)

    def on_encoder_setup(self, ws, consumer_id, pad_name, encoder: Gst.Element):
        if encoder.__gtype__.name != "GstOpusEnc":
            return

        # TODO: allow setting bitrate by user
        bitrate = 10000 if self.expect_video else 32000
        print(f"[{self.id}] Setting bitrate for {encoder} to {bitrate}")
        encoder.props.bitrate = bitrate

        return True

    def end_session(self, reason: str):
        if self.ws_session:
            self.ws_session.handle_player_session_ended(reason)

        self.gst_pipe.set_state(Gst.State.NULL)
        self.gst_bus.remove_watch()
        self.app.player_session_ended(self)

    def handle_ice_candidate(
        self,
        candidate: Optional[str],
        sdp_m_line_index: Optional[float],
        sdp_mid: Optional[str],
    ):
        self.gst_webrtc_signaller.emit(
            "handle-ice", self.id, sdp_m_line_index, sdp_mid, candidate
        )

    def handle_new_sdp(
        self,
        type: Literal["offer", "pranswer", "answer", "rollback"],
        sdp: Optional[str],
    ):
        if type == "offer" and self.is_making_offer:
            # Perfect negotiation: server is always impolite, because GstWebRTC
            # lack necessary changes in API to be able to perform offer rollback
            # atomically.
            # https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation
            # TODO: logging level
            print(f"[{self.id}] ignore incoming offer as we've offered ours")
            return

        webrtc_sdp = create_gst_webtrc_sdp(type, sdp)
        self.gst_webrtc_signaller.emit("session-description", self.id, webrtc_sdp)

    def handle_ws_disconnected(self):
        self.ws_session = None

    def bus_on_message(self, bus: Gst.Bus, msg: Gst.Message):
        if msg.type == Gst.MessageType.ERROR:
            err, debug_info = msg.parse_error()
            # TODO: log level
            print(f"GStreamer error: {err.message} (debug info: {debug_info})")

            self.end_session(f"Gstreamer error: {err.message}")
        elif msg.type == Gst.MessageType.EOS:
            # FIXME: determine if webrtc{sink,bin} somehow exposes latency
            # information, so that we don't cut off playback before it actually
            # finished on the client.
            delay = 1  # sec.
            self.event_loop.call_later(delay, self.end_session, "finished")

        return GLib.SOURCE_CONTINUE

    # Signal handlers that are called from webrtcsink
    def signaller_on_start(self, _):
        self.gst_webrtc_signaller.emit(
            "session-requested", self.id, f"{self.id}-recv", None
        )

        return True

    def signaller_on_stop(self, _):
        # TODO: assume session end?
        return True

    def signaller_on_send_session_description(self, _, session_id, offer):
        if not self.ws_session:
            return

        typ = "offer"
        if offer.type == GstWebRTC.WebRTCSDPType.ANSWER:
            typ = "answer"
        sdp = offer.sdp.as_text()
        self.ws_session.handle_player_send_sdp({"type": typ, "sdp": sdp})
        return True

    def signaller_on_send_ice(
        self, _, session_id, candidate, sdp_m_line_index, sdp_mid
    ):
        if not self.ws_session:
            return

        self.ws_session.handle_player_send_ice_candidate(
            {
                "candidate": candidate,
                "sdpMLineIndex": sdp_m_line_index,
                "sdpMid": sdp_mid,
            }
        )
        return True

    def signaller_on_end_session(self, _, session_id):
        self.event_loop.call_soon_threadsafe(self.end_session, "WebRTC session ended")
        return True

    def signaller_on_consumer_added(self, _, peer_id, webrtcbin):
        return True

    def signaller_on_consumer_removed(self, _, peer_id, webrtcbin):
        return True

    def signaller_on_webrtcbin_ready(self, _, peer_id, webrtcbin):
        return True
