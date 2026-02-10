# -*- coding: utf-8 -*-
"""
企业微信消息加解密模块
基于 AES-128-CBC 实现，参考企业微信官方 Python 示例
"""

import os
import base64
import hashlib
import time
import struct
import xml.etree.ElementTree as ET

from Crypto.Cipher import AES

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class WXBizMsgCrypt:
    """企业微信消息加解密"""

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        self.token = token
        self.corp_id = corp_id
        # EncodingAESKey 是 Base64 编码的 43 字符，补 '=' 后解码得到 32 字节 AES 密钥
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        if len(self.aes_key) != 32:
            raise ValueError(f"EncodingAESKey 解码后长度应为 32 字节，实际 {len(self.aes_key)}")

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """
        验证回调URL（GET请求）
        解密 echostr 并返回明文
        """
        signature = self._sha1_signature(self.token, timestamp, nonce, echostr)
        if signature != msg_signature:
            raise ValueError("签名验证失败")
        return self._decrypt(echostr)

    def decrypt_msg(self, msg_signature: str, timestamp: str, nonce: str, post_data: str) -> str:
        """
        解密接收到的消息（POST请求）
        从 XML 中提取 Encrypt 字段，验证签名后解密
        返回解密后的 XML 明文
        """
        xml_tree = ET.fromstring(post_data)
        encrypt = xml_tree.find("Encrypt").text
        signature = self._sha1_signature(self.token, timestamp, nonce, encrypt)
        if signature != msg_signature:
            raise ValueError("消息签名验证失败")
        return self._decrypt(encrypt)

    def encrypt_msg(self, reply_msg: str, nonce: str, timestamp: str = None) -> str:
        """
        加密回复消息
        返回加密后的 XML 字符串
        """
        timestamp = timestamp or str(int(time.time()))
        encrypt = self._encrypt(reply_msg)
        signature = self._sha1_signature(self.token, timestamp, nonce, encrypt)
        return (
            f"<xml>"
            f"<Encrypt><![CDATA[{encrypt}]]></Encrypt>"
            f"<MsgSignature><![CDATA[{signature}]]></MsgSignature>"
            f"<TimeStamp>{timestamp}</TimeStamp>"
            f"<Nonce><![CDATA[{nonce}]]></Nonce>"
            f"</xml>"
        )

    @staticmethod
    def _sha1_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
        """SHA1 签名"""
        sort_list = sorted([token, timestamp, nonce, encrypt])
        return hashlib.sha1("".join(sort_list).encode("utf-8")).hexdigest()

    def _encrypt(self, text: str) -> str:
        """AES-CBC 加密"""
        random_bytes = os.urandom(16)
        text_bytes = text.encode("utf-8")
        corp_id_bytes = self.corp_id.encode("utf-8")
        content = random_bytes + struct.pack("!I", len(text_bytes)) + text_bytes + corp_id_bytes
        padded = self._pkcs7_pad(content)
        iv = self.aes_key[:16]
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    def _decrypt(self, encrypt: str) -> str:
        """AES-CBC 解密"""
        iv = self.aes_key[:16]
        cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(base64.b64decode(encrypt))
        unpadded = self._pkcs7_unpad(decrypted)
        # 前16字节是随机字符串，接下来4字节是消息长度（网络字节序）
        msg_len = struct.unpack("!I", unpadded[16:20])[0]
        msg = unpadded[20:20 + msg_len].decode("utf-8")
        from_corp_id = unpadded[20 + msg_len:].decode("utf-8")
        if from_corp_id != self.corp_id:
            raise ValueError(f"CorpID 不匹配: 期望 {self.corp_id}, 实际 {from_corp_id}")
        return msg

    @staticmethod
    def _pkcs7_pad(data: bytes) -> bytes:
        """PKCS#7 填充（32字节块）"""
        block_size = 32
        padding = block_size - (len(data) % block_size)
        return data + bytes([padding] * padding)

    @staticmethod
    def _pkcs7_unpad(data: bytes) -> bytes:
        """PKCS#7 去填充"""
        padding = data[-1]
        if padding < 1 or padding > 32:
            padding = 0
        return data[:-padding]
