from typing_extensions import Literal, NotRequired, TypedDict, Union

class SessionDescription(TypedDict):
  sdp: NotRequired[str]
  type: Union[Literal["answer"],Literal["offer"],Literal["pranswer"],Literal["rollback"]]

class IceCandidate(TypedDict):
  candidate: NotRequired[str]
  sdpMLineIndex: NotRequired[float]
  sdpMid: NotRequired[str]
  usernameFragment: NotRequired[str]

class NewSessionMessage(TypedDict):
  type: Literal["newSession"]
  videoUrl: str
  wantVideo: NotRequired[bool]

class ResumeSessionMessage(TypedDict):
  type: Literal["resumeSession"]
  sessionId: str

class EndSessionMessage(TypedDict):
  type: Literal["endSession"]

class SessionConnectedMessage(TypedDict):
  type: Literal["sessionConnected"]
  sessionId: str

class SessionEndedMessage(TypedDict):
  type: Literal["sessionEnded"]
  sessionId: NotRequired[str]
  reason: str

class IceCandidateMessage(TypedDict):
  type: Literal["iceCandidate"]
  candidate: IceCandidate

class NewSdpMessage(TypedDict):
  type: Literal["newSdp"]
  sdp: SessionDescription

Message = Union[NewSessionMessage,ResumeSessionMessage,EndSessionMessage,SessionConnectedMessage,SessionEndedMessage,IceCandidateMessage,NewSdpMessage]
