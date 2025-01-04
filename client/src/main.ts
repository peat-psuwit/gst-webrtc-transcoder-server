import App from "./app";

function constructWsServer() {
    let url = new URL(window.location.toString());
    url.pathname = "/ws";
    return url.toString();
}

let app = new App({
    wsServer: constructWsServer(),
    iceServers: [
        // https://groups.google.com/g/discuss-webrtc/c/shcPIaPxwo8
        // > The Google STUN server is something you can freely use for
        // > development purposes, but, as a free service, there is no SLA.
        // > If you are deploying a commercial application, you should plan to
        // > deploy your own STUN/TURN servers."
        { urls: "stun:stun.l.google.com:19302" },
    ],
}, document);
