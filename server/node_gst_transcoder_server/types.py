class RawMedia:
    url: str
    expect_video: bool
    expect_audio: bool

    def __init__(self, url, expect_video=False, expect_audio=False):
        if not expect_video and not expect_audio:
            raise Exception("RawMedia must contain video or audio")

        self.url = url
        self.expect_video = expect_video
        self.expect_audio = expect_audio
