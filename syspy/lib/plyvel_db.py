import logging
import os
import pickle

import fasteners
import plyvel

log = logging.getLogger("rbk.script")


class LevelDB:
    _db_path = "/opt/.data/rbk/private/runtimes/containers_leveldb"
    _lock_file_path = os.path.join('/tmp', 'containers_leveldb.lock')  # 分离锁文件路径
    _db = None
    _lock = fasteners.InterProcessLock(_lock_file_path)

    @staticmethod
    def _to_bytes(data):
        if isinstance(data, bytes):
            return data
        else:
            return pickle.dumps(data)

    @staticmethod
    def _from_bytes(data):
        try:
            return pickle.loads(data)
        except pickle.UnpicklingError:
            return data.decode('utf-8')

    @classmethod
    def init_db(cls):
        if cls._db is None:
            with cls._lock:  # 确保初始化时只有一个进程创建数据库
                if cls._db is None:  # 双重检查lock
                    try:
                        cls._db = plyvel.DB(cls._db_path, create_if_missing=True)
                    except Exception as e:
                        log.error("LevelDB: Failed to initialize database: %s", e)
                        return False
        return True

    @classmethod
    def put(cls, key: str, value):
        cls.init_db()
        with cls._lock:  # 写锁
            try:
                cls._db.put(cls._to_bytes(key), cls._to_bytes(value))
                log.info("LevelDB: Data put successfully: %s -> %s", key, value)
                return True
            except Exception as e:
                log.error("LevelDB: Failed to put data into database: %s", e)
                return False

    @classmethod
    def put_all(cls, value):
        cls.init_db()
        with cls._lock:  # 写锁
            try:
                with cls._db.write_batch() as batch:
                    for key in cls._db.iterator(include_value=False):
                        batch.put(key, cls._to_bytes(value))
                        log.info("LevelDB: Data put successfully: %s -> %s", key, value)
                    batch.write()
                    return True
            except Exception as e:
                log.error("LevelDB: Failed to put data into database: %s", e)
                return False

    @classmethod
    def get(cls, key: str):
        cls.init_db()
        try:
            result = cls._db.get(cls._to_bytes(key))
            if result is None:
                log.error("LevelDB: Key not found: %s", key)
                return None
            return cls._from_bytes(result)  # 返回原始数据类型
        except Exception as e:
            log.error("LevelDB: Failed to get data from database: %s", e)
            return None

    @classmethod
    def get_all(cls):
        cls.init_db()
        try:
            result = {}
            for key, value in cls._db.iterator():
                result[cls._from_bytes(key)] = cls._from_bytes(value)
            return result
        except Exception as e:
            log.error("LevelDB: Failed to get all data from database: %s", e)
            return None

    @classmethod
    def delete(cls, key: str):
        cls.init_db()
        with cls._lock:  # 写锁
            try:
                cls._db.delete(cls._to_bytes(key))
                log.info("LevelDB: Data deleted successfully: '%s'", key)
                return True
            except Exception as e:
                log.error("LevelDB: Failed to delete data '%s' from database: %s", key, e)
                return False

    @classmethod
    def delete_all(cls):
        """清空数据库中所有键值对."""
        cls.init_db()
        with cls._lock:  # 加锁确保多进程安全
            try:
                # 使用 write_batch 批量删除所有 key
                batch = cls._db.write_batch()
                for key, _ in cls._db.iterator():
                    batch.delete(key)
                batch.write()
                log.info("LevelDB: Successfully deleted all entries from database.")
                return True
            except Exception as e:
                log.error("LevelDB: Failed to delete all entries from database: %s", e)
                return False

    @classmethod
    def close_db(cls):
        if cls._db is not None:
            cls._db.close()
            cls._db = None
            log.info("LevelDB: Database connection closed successfully")
            return True
        log.info("LevelDB: Database connection was already closed")
        return True

    @classmethod
    def get_db(cls) -> plyvel.DB:
        return cls._db


# 示例使用方法
if __name__ == '__main__':
    LevelDB.put('key1', 'value1')
    LevelDB.put('key2', 123)
    LevelDB.put('key3', {'name': 'value3'})
    print("db.get('key1'):", LevelDB.get('key1'))
    print("db.get('key2'):", LevelDB.get('key2'))
    result = LevelDB.get('key3')
    print("type(db.get('key3')):", type(result))
    print("db.get('key3'):", result)

    LevelDB.delete('key1')
    print("db.get('key1'):", LevelDB.get('key1'))
