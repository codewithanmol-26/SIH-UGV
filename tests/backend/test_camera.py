from pathlib import Path

from perception.camera import VideoFileSource, IPStreamSource, RTSPSource

SAMPLE_VIDEO = str(Path(__file__).resolve().parent.parent.parent / "sample_data" / "sample_outdoor.mp4")


def test_video_file_source_opens_and_reads_frames():
    cam = VideoFileSource(SAMPLE_VIDEO)
    assert cam.open()
    frame = cam.read()
    assert frame is not None
    assert frame.image.shape[2] == 3
    cam.release()


def test_video_file_source_loops_past_eof():
    cam = VideoFileSource(SAMPLE_VIDEO)
    cam.open()
    # Read well past the short sample clip's frame count; loop_video=True
    # means this should never return None.
    frames_read = 0
    for _ in range(80):
        frame = cam.read()
        assert frame is not None
        frames_read += 1
    assert frames_read == 80
    cam.release()


def test_video_file_source_is_stale_before_open():
    cam = VideoFileSource(SAMPLE_VIDEO)
    # No frame read yet -> is_stale should not false-positive.
    assert cam.is_stale(timeout_s=1.0) is False


def test_unimplemented_sources_are_honestly_labelled():
    ip_cam = IPStreamSource(url="http://192.0.2.1:8080/video")
    rtsp_cam = RTSPSource(url="rtsp://192.0.2.1/stream")
    assert ip_cam.open() is False
    assert rtsp_cam.open() is False
    assert ip_cam.read() is None
    assert rtsp_cam.read() is None
