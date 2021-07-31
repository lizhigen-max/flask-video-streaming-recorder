import cv2
import threading
from datetime import datetime
import time
from queue import Queue

queueDic = {}

class RecordingThread(threading.Thread):
    def __init__(self, name, camera):
        threading.Thread.__init__(self)
        self.name = name
        self.isRunning = True

        self.cap = camera

    def run(self):
        global queueDic
        queue = Queue(maxsize=32)
        queueDic.setdefault(self, queue)

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.videoPath = 'video_{}.avi'.format(self.ident)
        self.out = cv2.VideoWriter('controller/static/' + self.videoPath, fourcc, 20.0, (640, 480))

        while self.isRunning:
            if queue and not queue.empty():
                frame = queue.get()
                self.out.write(frame)
            else:
                time.sleep(0.01)

        queue.queue.clear()
        del queueDic[self]
        self.out.release()

    def stop(self):
        self.isRunning = False

    def __del__(self):
        self.out.release()


class VideoCamera(object):
    def __init__(self):
        # 打开摄像头， 0代表笔记本内置摄像头
        self.cap = cv2.VideoCapture(0)
        self.lock = threading.RLock()
        print('Only one instance will be generated!')

        # 视频录制线程
        self.recordingThread = None


    # 退出程序释放摄像头
    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

    def get_frame(self):
        # todo: 如果太多线程，理论上这里可能会造成保存的视频卡顿，因为多线程queue会保存很多图片

        global queueDic
        self.lock.acquire()
        ret, f = self.cap.read()
        self.lock.release()
        for thread, queue in queueDic.items():
            if thread and thread.is_alive():
                frame = f.copy()
                if queue.full():
                    queue.get()  # 如果队列已满，删除一个元素
                queue.put(frame)
            else:
                del queueDic[thread]

        if ret:
            ret, jpeg = cv2.imencode('.jpg', f)
            return jpeg.tobytes()

        else:
            return None

    def start_record(self):
        recordingThread = RecordingThread("Video Recording Thread", self.cap)
        recordingThread.start()
        return recordingThread.ident

    def stop_record(self, id):
        global queueDic
        for thread, queue in queueDic.items():
            if thread.ident == id:
                path = thread.videoPath
                thread.stop()
                thread = None
                return path
        return None

singleton = VideoCamera()