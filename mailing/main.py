from mailing.config import conf
import asyncio
import multiprocessing

if __name__ == '__main__':
    process = multiprocessing.Process(target=asyncio.run(conf.app.run()))
    process.start()
    process.join()


