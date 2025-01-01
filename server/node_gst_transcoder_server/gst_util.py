import gi

from typing import Literal, Optional

gi.require_version("GstSdp", "1.0")
gi.require_version("GstWebRTC", "1.0")

from gi.repository import GstSdp
from gi.repository import GstWebRTC


def create_gst_webtrc_sdp(
    type: Literal["offer", "pranswer", "answer", "rollback"],
    sdp: Optional[str],
):
    match type:
        case "offer":
            sdpType = GstWebRTC.WebRTCSDPType.OFFER
        case "pranswer":
            sdpType = GstWebRTC.WebRTCSDPType.PRANSWER
        case "answer":
            sdpType = GstWebRTC.WebRTCSDPType.ANSWER
        case "rollback":
            sdpType = GstWebRTC.WebRTCSDPType.ROLLBACK

    _, sdpMsg = GstSdp.SDPMessage.new_from_text(sdp)

    return GstWebRTC.WebRTCSessionDescription.new(sdpType, sdpMsg)
