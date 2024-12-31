import gi

gi.require_version("GstSdp", "1.0")
gi.require_version("GstWebRTC", "1.0")

from gi.repository import GstSdp
from gi.repository import GstWebRTC

from .msgs import SessionDescription, IceCandidate


def gst_webtrc_sdp_from_web_sdp(sdp: SessionDescription):
    match sdp["type"]:
        case "offer":
            sdpType = GstWebRTC.WebRTCSDPType.OFFER
        case "pranswer":
            sdpType = GstWebRTC.WebRTCSDPType.PRANSWER
        case "answer":
            sdpType = GstWebRTC.WebRTCSDPType.ANSWER
        case "rollback":
            sdpType = GstWebRTC.WebRTCSDPType.ROLLBACK

    if "sdp" in sdp:
        _, sdpMsg = GstSdp.SDPMessage.new_from_text(sdp["sdp"])
    else:
        # TODO: valid?
        sdpMsg = None

    return GstWebRTC.WebRTCSessionDescription.new(sdpType, sdpMsg)
