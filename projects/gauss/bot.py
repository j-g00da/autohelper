from threading import Thread

from autohelper import configure, run, script_run

__all__ = ("configure", "run", "script_run")

if __name__ == "__main__":
    t1 = Thread(target=script_run, args=(__name__,))
    t2 = Thread(target=script_run, args=(__name__,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
