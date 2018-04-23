# -*- coding: utf8 -*-
import time
import rsa
import base64
import hashlib
import random


class ChargeSDK(object):

    def __init__(self, token, ts, sec, ver):
        self._token = token
        self._ts = ts
        self._sec = sec
        self._ver = ver

    def get_open_info(self):
        if not (self._token and self._ts and self._sec and self._ver):
            return {}
        if abs(time.time() - int(self._ts)) > 3600:
            return {}
        if self._verify_key():
            info = dict(
                openid=self._token,
                nickname=u'用户%s%s' % (self._token[-4:], random.randint(1000, 9999)),
                name='$mg$%s' % (self._token),
            )
            return info

        return {}

    def _verify_key(self):
        if self._ver != '1' or len(self._sec) != 172:
            return False

        pk_1024_pem = """-----BEGIN RSA PRIVATE KEY-----
        MIICXQIBAAKBgQC/maA4kML59n6Rwrrm8FHT8SAGcFGI+cYejWS6vlY5BVHNNMLW
        jKGv71dvGT/7tET5I8b/X2WCQkM7/g/hTzH34rVmKWH+87KB9mCwnOguBlvohzMe
        6+jnrpzLXXLqv7OfMVTKmMV1Q52M8FO0Xu5tQITECTipe27GrzSskN3qrwIDAQAB
        AoGBAKmWuRJYT7wgSfeKfRRcMpF+I/KPCBxNuObiD/6a6oaeBsGzqaFt6M9o8eMM
        Xm3UKhi7ajAvqBGbxRcc0cGD750Joc9eyYAoxxJ9IHka0nEHKt+qOCDQK/LANl7x
        E3H++COGK0zs0mjdqDoPKaCmEGYD9x3VmJs8/KZFVXDrojgBAkEA32dMWHmMDOPI
        QlA8N69VG0zNSwtx5TQYXc1xm7i9aIoC7duZZ5oWrBL7Vgp7SQUVJbYn+6M8gBil
        D6QiB75YLwJBANuOYz+xV3WNCvVCqrdKqNw/sR6a71QcNOgNvTb3WRLEM7tFI2MY
        I2Jm10NZAV/6Tt7oBYZn6cwZJPf0AR86dYECQFfFKcWI23Ek/MSw6TendvRm1DEr
        qe+26+vOj1fy2Nd9gXEZ2cdOTqIEQyKms5EYohpS2pqOo3JgPFlMzuHj8pkCQQDL
        CkewfFF0TUYIAGod7XZxkJk8w212rEslGqeUMHR4TWfF1K9gEc+PTanfB22lE7di
        ntGVNX3aGJq+jzGGbqqBAkAfSjvlQvm8JCEsAxy3pwiWrQ5oPT+/xj56+/my0GMr
        9etjDXGXnn0xJDtbnBlSfV5dYRoENPQ7OpmI2s6zX2u0
        -----END RSA PRIVATE KEY-----"""
        try:
            privatekey = rsa.PrivateKey.load_pkcs1(pk_1024_pem)
            message = rsa.decrypt(base64.b64decode(self._sec), privatekey)
            sig = hashlib.md5(self._token + self._ts).digest()
            if message == sig:
                return True
            else:
                return False
        except:
            pass

        return False
