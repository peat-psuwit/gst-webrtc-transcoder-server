from typing_extensions import Literal, NotRequired, TypedDict, Union

class Ts2Py_Lj3BsgI4Uc(TypedDict):
  sdp: NotRequired[str]
  type: Literal["offer"]

class NewSessionMessage(TypedDict):
  type: Literal["newSession"]
  videoUrl: str
  sdp: Ts2Py_Lj3BsgI4Uc

class ResumeSessionMessage(TypedDict):
  type: Literal["resumeSession"]
  sessionId: str
  sdp: Ts2Py_Lj3BsgI4Uc

class EndSessionMessage(TypedDict):
  type: Literal["endSession"]

class Ts2Py_KgNjcSLwUP(TypedDict):
  sdp: NotRequired[str]
  type: Literal["answer"]

class SessionConnectedMessage(TypedDict):
  type: Literal["sessionConnected"]
  sessionId: str
  sdp: Ts2Py_KgNjcSLwUP

class SessionEndedMessage(TypedDict):
  type: Literal["sessionEnded"]
  reason: str

class Ts2Py_3BpyxWIxju(TypedDict):
  candidate: NotRequired[str]
  sdpMLineIndex: NotRequired[float]
  sdpMid: NotRequired[str]
  usernameFragment: NotRequired[str]

class IceCandidateMessage(TypedDict):
  type: Literal["iceCandidate"]
  candidate: Ts2Py_3BpyxWIxju

class Ts2Py_PRw0YAtmZf(TypedDict):
  sdp: NotRequired[str]
  type: Union[Literal["answer"],Literal["offer"],Literal["pranswer"],Literal["rollback"]]

class NewSdpMessage(TypedDict):
  type: Literal["newSdp"]
  sdp: Ts2Py_PRw0YAtmZf

Message = Union[NewSessionMessage,ResumeSessionMessage,EndSessionMessage,SessionConnectedMessage,SessionEndedMessage,IceCandidateMessage,NewSdpMessage]
