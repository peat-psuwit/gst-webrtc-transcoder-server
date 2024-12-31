import asyncio


async def extract_media_url_from_video_url(video_url: str):
    # TODO: more sophisticated stuffs
    process = await asyncio.create_subprocess_exec(
        "yt-dlp",
        "-v",
        "-g",
        "-f",
        "bestaudio/best",
        "--format-sort",
        "+size,+br,+res,+fps",
        video_url,
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    # TODO: error checking
    result = stdout.decode()

    return result
