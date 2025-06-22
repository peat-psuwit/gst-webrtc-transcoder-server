import asyncio

from .types import RawMedia


async def extract_media_url_from_video_url(video_url: str, want_video: bool):
    # TODO: more sophisticated stuffs

    if want_video:
        # Try to pick an up to 240p video, so that when further downscaled it's
        # not half bad. Failing that, just picking any smallest video.
        ytdlp_format = (
            'worstvideo[height<=240]+bestaudio'
            '/bestvideo+bestaudio'
            '/best'
        )
    else:
        ytdlp_format = 'bestaudio/best'

    process = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "-v",
        "-g",
        "-f",
        ytdlp_format,
        "--format-sort",
        "+size,+br,+res,+fps",
        video_url,
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    # TODO: error checking
    result = stdout.decode()
    urls = result.splitlines()

    if len(urls) == 0:
        return None

    if len(urls) == 1:
        return [RawMedia(urls[0], expect_audio=True, expect_video=want_video)]

    return [
        RawMedia(urls[0], expect_video=True),
        RawMedia(urls[1], expect_audio=True),
    ]
