# source/

Drop raw videos here to hand them to a cloud session, which cannot reach your
local disk or Google Drive.

    git checkout claude/great-gauss-i4gkj2
    cp "/c/path/to/video.mp4" source/
    git add source/ && git commit -m "Add <name> for editing" && git push

Videos are tracked by Git LFS (see `.gitattributes`), so they do not bloat the
repository the way an ordinary binary blob would. Run `git lfs install` once on
each machine before the first push, or git stores them as plain blobs instead.

GitHub rejects any single file over 100 MB even through LFS on the free tier's
default limits, and LFS bandwidth is quota'd. For a long recording, trim the
moment you actually want first — it is faster to move and it is the first step
of the edit anyway:

    ffmpeg -ss 00:04:30 -i input.mp4 -t 40 -c copy source/moment.mp4

Finished edits are written to `shorts/`, not here.
