import asyncio
import gi

from typing import Literal, Optional, TYPE_CHECKING

from .gst_util import create_gst_webtrc_sdp

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")

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


class PlayerSession:
    id: str
    media_url: str
    ws_session: Optional[WsSession]
    app: App
    event_loop: asyncio.AbstractEventLoop

    gst_pipe: Gst.Pipeline
    gst_dec: Gst.Element
    gst_webrtc: Gst.Element
    gst_webrtc_signaller: GObject.Object

    is_making_offer: bool

    def __init__(
        self,
        id: str,
        media_url: str,
        ws_session: WsSession,
        app: App,
        event_loop: asyncio.AbstractEventLoop,
        initial_offer: str,
    ):
        self.id = id
        self.media_url = media_url
        self.ws_session = ws_session
        self.app = app
        self.event_loop = event_loop
        self.is_making_offer = False

        self.gst_pipe = Gst.parse_launch_full(
            "urldecodebin name=dec ! audio/x-raw ! webrtcsink name=webrtc",
            None,  # GstParseContext
            Gst.ParseFlags.FATAL_ERRORS,
        )

        self.gst_dec = self.gst_pipe.get_by_name("dec")
        self.gst_dec.props.url = self.media_url

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
        self.gst_webrtc_signaller.connect(
            "webrtcbin-ready", self.signaller_on_webrtcbin_ready
        )
        self.gst_pipe.set_state(Gst.State.PLAYING)

        webrtc_sdp = create_gst_webtrc_sdp("offer", initial_offer)
        self.gst_webrtc_signaller.emit(
            "session-requested", f"{self.id}-send", f"{self.id}-recv", webrtc_sdp
        )

    def on_encoder_setup(self, ws, consumer_id, pad_name, encoder: Gst.Element):
        if encoder.__gtype__.name != "GstOpusEnc":
            return

        # TODO: allow setting bitrate by user
        bitrate = 40000
        print(f"[{self.id}] Setting bitrate for {encoder} to {bitrate}")
        encoder.props.bitrate = bitrate

        return True

    def end_session(self, reason: str):
        if self.ws_session:
            self.ws_session.handle_player_session_ended(reason)

        self.gst_pipe.set_state(Gst.State.NULL)
        self.app.player_session_ended(self)

    def handle_ice_candidate(
        self,
        candidate: Optional[str],
        sdp_m_line_index: Optional[float],
        sdp_mid: Optional[str],
    ):
        self.gst_webrtc_signaller.emit(
            "handle-ice", f"{self.id}-send", sdp_m_line_index, sdp_mid, candidate
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
        self.gst_webrtc_signaller.emit(
            "session-description", f"{self.id}-send", webrtc_sdp
        )

    def handle_ws_disconnected(self):
        self.ws_session = None

    # Signal handlers that are called from webrtcsink
    def signaller_on_start(self, _):
        # Do nothing. We _are_ the signal server.
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
