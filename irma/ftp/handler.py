#
# Copyright (c) 2013-2014 QuarksLab.
# This file is part of IRMA project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the top-level directory
# of this distribution and at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# No part of the project, including this file, may be copied,
# modified, propagated, or distributed except according to the
# terms contained in the LICENSE file.

import logging
import hashlib
from ..common.exceptions import IrmaFtpError
from ftplib import FTP_TLS
import ssl

log = logging.getLogger(__name__)


class FTP_TLS_Data(FTP_TLS):
    """
    Only improvement is to allow transfer of data
    directly instead of reading data from fp
    """

    def storbinarydata(self,
                       cmd,
                       data,
                       blocksize=8192,
                       callback=None,
                       rest=None):
        self.voidcmd('TYPE I')
        conn = self.transfercmd(cmd, rest)
        try:
            index = 0
            while 1:
                buf = data[index:index + blocksize]
                index += blocksize
                if len(buf) == 0:
                    break
                conn.sendall(buf)
                if callback:
                    callback(buf)
            # shutdown ssl layer
            if isinstance(conn, ssl.SSLSocket):
                conn.unwrap()
        finally:
            conn.close()
        return self.voidresp()


class FtpTls(object):
    """Internal database.

    This class handles the conection with ftp server over tls
    functions for interacting with it.
    """
    # hash function for integrity
    # each uploaded file is renamed after its digest value
    # and checked at retrieval
    hashfunc = hashlib.sha256

    # ==================================
    #  Constructor and Destructor stuff
    # ==================================
    def __init__(self, host, port, user, passwd):
        self._host = host
        self._port = port
        # TODO support connection on non standard port
        if self._port != FTP_TLS.port:
            reason = ("connection supported " +
                      "only on port {0}".format(FTP_TLS.port))
            raise IrmaFtpError(reason)
        self._user = user
        self._passwd = passwd
        self._conn = None
        self._connect()

    def __del__(self):
        try:
            if self._conn is not None:
                self._disconnect()
        except AttributeError:
            # if exception raised in init
            # there is no _conn
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.__del__()

    # =================
    #  Private methods
    # =================

    def _connect(self):
        if self._conn is not None:
            log.warn("Already connected to ftp server")
        try:
            self._conn = FTP_TLS_Data(self._host, self._user, self._passwd)
            # Explicitly ask for secure data channel
            self._conn.prot_p()
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def _disconnect(self):
        if self._conn is None:
            return
        try:
            self._conn.close()
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def _hash(self, data):
        try:
            return self.hashfunc(data).hexdigest()
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def _check_hash(self, digest, data):
        try:
            if self.hashfunc(data).hexdigest() != digest:
                raise IrmaFtpError("Integrity check file failed")
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    # ================
    #  Public methods
    # ================

    def mkdir(self, path):
        try:
            self._conn.mkd(path)
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))
        return

    def list(self, path):
        """ list remote directory <path>"""
        try:
            return self._conn.nlst(path)
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def upload_data(self, path, data):
        """ Upload <data> to remote directory <path>"""
        try:
            dstname = self._hash(data)
            dstpath = "{0}/{1}".format(path, dstname)
            self._conn.storbinarydata("STOR {0}".format(dstpath),
                                      data)
            return dstname
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def upload_file(self, path, filename):
        """ Upload <filename> content into directory <path>"""
        try:
            with open(filename, "rb") as f:
                dstname = self.upload_data(path, f.read())
                return dstname
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def download(self, path, remotename, dstname):
        """ Download <remotename> found in <path> to <dstname>"""
        try:
            data = []
            with open(dstname, 'wb') as f:
                dstpath = "{0}/{1}".format(path, remotename)
                self._conn.retrbinary("RETR {0}".format(dstpath),
                                      lambda x: data.append(x))
                buf = ''.join(data)
                # remotename is hashvalue of data
                self._check_hash(remotename, buf)
                f.write(buf)
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def delete(self, path, filename):
        """ Delete <filename> into directory <path>"""
        try:
            self._conn.delete("{0}/{1}".format(path, filename))
        except Exception as e:
            raise IrmaFtpError("{0}".format(e))

    def deletepath(self, path, deleteParent=False):
        # recursively delete all subdirs and files
        try:
            for f in self.list(path):
                if self.is_file(path, f):
                    self.delete(path, f)
                else:
                    self.deletepath("{0}/{1}".format(path, f),
                                    deleteParent=True)
            if deleteParent:
                self._conn.rmd(path)
        except Exception as e:
            reason = "{0} [{1}]".format(e, path)
            raise IrmaFtpError(reason)

    def is_file(self, path, filename):
        try:
            pathfilename = "{0}/{1}".format(path, filename)
            current = self._conn.pwd()
            self._conn.cwd(pathfilename)
            self._conn.cwd(current)
            return False
        except:
            return True
