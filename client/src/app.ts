import type { Config } from "./types"
import type { Message } from "./msgs";

export default class App {
    document: Document
    config: Config;
    sessionId: string | null;
    startingSession: boolean;
    endingSession: boolean;
    reconnectAttempt: number;
    maxReconnectDelay: number;

    // Assigned in reset_webrtc(), called from constructor.
    webrtc!: RTCPeerConnection;
    // Assigned in reset_ws(), called from constructor.
    ws!: WebSocket;

    video_form: HTMLFormElement
    video_url_input: HTMLInputElement
    video_form_submit: HTMLButtonElement
    video_stop_btn: HTMLButtonElement
    want_video_input: HTMLInputElement
    status_div: HTMLDivElement
    media_player_holder: HTMLDivElement
    media_player: HTMLMediaElement | null

    constructor(config: Config, document: Document) {
        this.document = document;
        this.config = config;
        this.sessionId = null;
        this.startingSession = false;
        this.endingSession = false;
        this.reconnectAttempt = 0;
        this.maxReconnectDelay = 8000;

        // TODO: better way than interogate document?
        this.video_form = <HTMLFormElement>document.getElementById("video-form");
        this.video_url_input = <HTMLInputElement>document.getElementById("video-url");
        this.video_form_submit = <HTMLButtonElement>document.getElementById("video-form-submit");
        this.video_stop_btn = <HTMLButtonElement>document.getElementById("video-stop");
        this.want_video_input = <HTMLInputElement>document.getElementById("want-video");
        this.status_div = <HTMLDivElement>document.getElementById("status");
        this.media_player_holder = <HTMLDivElement>document.getElementById("media-player-holder");
        this.media_player = null;

        this.video_form.addEventListener("submit", this.handle_video_form_submit);
        this.video_stop_btn.addEventListener("click", this.handle_video_stop_btn);

        this.reset_webrtc();
        this.reset_ws();
    }

    set_status(status: string) {
        this.status_div.innerText = status;
    }

    update_ui() {
        if (this.ws.readyState == WebSocket.OPEN &&
            !this.sessionId && !this.startingSession && !this.endingSession
        ) {
            this.video_url_input.removeAttribute("disabled");
            this.video_form_submit.removeAttribute("disabled");
            this.want_video_input.removeAttribute("disabled");
        } else {
            this.video_url_input.setAttribute("disabled", "");
            this.video_form_submit.setAttribute("disabled", "");
            this.want_video_input.setAttribute("disabled", "");
        }

        if (this.sessionId && !this.startingSession && !this.endingSession) {
            this.video_stop_btn.removeAttribute("disabled");
        } else {
            this.video_stop_btn.setAttribute("disabled", "");
        }
    }

    reset_ws() {
        if (this.ws) {
            this.ws.close();
        }

        this.ws = new WebSocket(this.config.wsServer);
        this.ws.addEventListener("open", this.handle_ws_open);
        this.ws.addEventListener("message", this.handle_ws_message);
        this.ws.addEventListener("close", this.handle_ws_close);

        this.startingSession = false;
        this.endingSession = false;
    }

    ws_send(msg: Message) {
        this.ws.send(JSON.stringify(msg));
    }

    handle_ws_open = () => {
        if (this.sessionId) {
            this.set_status("Connected, but session resumption is not yet implemented.");
        } else {
            this.set_status("Connected to server.");
        }

        this.reconnectAttempt = 0;

        this.update_ui();
    }

    handle_ws_message = async (e: MessageEvent) => {
        if (typeof e.data !== "string") {
            this.set_status("Huh? Server sent binary data?");
            return;
        }

        // XXX: no validation whatsoever
        let msg = <Message> JSON.parse(e.data);
        switch (msg.type) {
            case "sessionConnected":
                this.video_url_input.value = "";
                this.sessionId = msg.sessionId;
                this.startingSession = false;
                // Answer SDP will come from newSdp event.
                break;
            case "newSdp":
                // Perfect negotiation: client is always polite, as GstWebRTC
                // doesn't have necessary changes to rollback offer atomically.
                // Being polite means we accept any offer from remote side, even
                // if we've just sent another offer.
                // https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Perfect_negotiation
                await this.webrtc.setRemoteDescription(msg.sdp);
                if (msg.sdp.type == "offer") {
                    await this.webrtc.setLocalDescription();
                    this.ws_send({
                        type: "newSdp",
                        // Because we've called setLocalDescription(), it's
                        // guaranteed to be there.
                        sdp: this.webrtc.localDescription!,
                    });
                }

                break;
            case "iceCandidate":
                // XXX: we're going to receive only, but still. :P
                this.webrtc.addIceCandidate(msg.candidate);
                break;
            case "sessionEnded":
                if (this.sessionId && msg.sessionId &&
                    this.sessionId !== msg.sessionId
                ) {
                    // Race condition.
                    break;
                }

                this.set_status(`Playback ended: ${msg.reason}`);

                this.reset_webrtc();
                this.sessionId = null;
                this.startingSession = false;
                this.endingSession = false;

                break;
        }

        this.update_ui();
    }

    handle_ws_close = () => {
        const delay = Math.min(this.maxReconnectDelay, 1000 * Math.pow(2, this.reconnectAttempt));
        this.reconnectAttempt++;

        this.set_status(
            `WebSocket connection unexpectedly closed. Trying to reconnect in ${delay / 1000}s.`);

        setTimeout(() => {
            this.reset_ws();
        }, delay);

        this.update_ui();
    }

    reset_webrtc() {
        if (this.webrtc) {
            if (this.media_player)
                this.media_player.srcObject = null;
            this.webrtc.close();
        }

        this.webrtc = new RTCPeerConnection({
            iceServers: this.config.iceServers,
        });

        this.webrtc.addEventListener("track", this.handle_webrtc_track);
        this.webrtc.addEventListener("negotiationneeded",
            this.handle_webrtc_negotiation_needed);
        this.webrtc.addEventListener("icecandidate",
            this.handle_webrtc_ice_candidate);
    }

    handle_webrtc_track = ({ track, streams }: RTCTrackEvent) => {
        track.addEventListener("unmute", () => {
            if (!this.media_player) {
                // ???
                return;
            }

            if (this.media_player.srcObject) {
                // ???
                return;
            }
            this.media_player.srcObject = streams[0];
        }, { once: true });
    }

    handle_webrtc_negotiation_needed = async () => {
        try {
            await this.webrtc.setLocalDescription();
            this.ws_send({
                type: "newSdp",
                sdp: this.webrtc.localDescription!,
            });
        } catch (err) {
            // XXX: what can we do?
            console.error(err);
        }
    }

    handle_webrtc_ice_candidate = (e: RTCPeerConnectionIceEvent) => {
        if (!e.candidate) {
            console.log("ICE gathering is complete");
            return;
        }

        this.ws_send({
            type: "iceCandidate",
            candidate: e.candidate.toJSON(),
        })
    }

    handle_video_form_submit = async (ev: SubmitEvent) => {
        ev.preventDefault();

        let video_url = this.video_url_input.value;

        let wantVideo = this.want_video_input.checked;

        if (wantVideo)
            this.media_player = this.document.createElement("video");
        else
            this.media_player = this.document.createElement("audio");

        this.media_player.setAttribute("autoplay", "");
        this.media_player.setAttribute("controls", "");
        this.media_player_holder.replaceChildren(this.media_player);

        this.startingSession = true;
        this.set_status("Starting playback...");
        this.update_ui();

        this.ws_send({
            type: "newSession",
            videoUrl: video_url,
            wantVideo,
        });
    }

    handle_video_stop_btn = () => {
        if (this.ws.readyState == WebSocket.OPEN) {
            this.endingSession = true;

            this.set_status("Stopping playback...");
            this.ws_send({
                type: "endSession",
            });
        } else {
            this.reset_webrtc();
            this.sessionId = null;
            this.startingSession = false;
            this.endingSession = false;

            this.set_status("Playback reset.")
        }

        this.update_ui();
    }
}
