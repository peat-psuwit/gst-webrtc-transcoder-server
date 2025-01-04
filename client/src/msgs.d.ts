// For benefit of Python.
export type SessionDescription = RTCSessionDescriptionInit;
export type IceCandidate = RTCIceCandidateInit;

export type NewSessionMessage = {
    type: "newSession",
    videoUrl: string,
    sdp: RTCSessionDescriptionInit,
};

export type ResumeSessionMessage = {
    type: "resumeSession",
    sessionId: string,
    // We assume that we always want to re-negotiate on re-connect.
    sdp: RTCSessionDescriptionInit,
};

export type EndSessionMessage = {
    type: "endSession",
}

// Session is bound to WebSocket connection
export type SessionConnectedMessage = {
    type: "sessionConnected",
    sessionId: string,
};

// Used on both EOF and unsuccessful "resumeSession"
// TODO: We may want to re-think about this...
export type SessionEndedMessage = {
    type: "sessionEnded",
    // To avoid race condition.
    sessionId?: string,
    reason: string,
}

export type IceCandidateMessage = {
    type: "iceCandidate",
    candidate: RTCIceCandidateInit,
};

// Used for re-negotiation on both sides.
export type NewSdpMessage = {
    type: "newSdp",
    sdp: RTCSessionDescriptionInit,
}

export type Message = NewSessionMessage
                    | ResumeSessionMessage
                    | EndSessionMessage
                    | SessionConnectedMessage
                    | SessionEndedMessage
                    | IceCandidateMessage
                    | NewSdpMessage;
