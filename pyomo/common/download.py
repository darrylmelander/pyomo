#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________

import gzip
import io
import logging
import os
import platform
import ssl
import sys
import zipfile

from six.moves.urllib.request import urlopen
import pyomo.common
from pyomo.common.config import PYOMO_CONFIG_DIR

logger = logging.getLogger('pyomo.common.download')

DownloadFactory = pyomo.common.Factory('library downloaders')

class FileDownloader(object):
    def __init__(self, insecure=False, cacert=None):
        self.insecure = insecure
        self.cacert = cacert
        self.fname = None

    def get_sysinfo(self):
        """Return a tuple (platform_name, bits) for the current system

        Returns
        -------
           platform_name (str): lower case, usually in {linux, windows,
              cygwin, darwin}.
           bits (int): OS address width in {32, 64}
        """

        system = platform.system().lower()
        for c in '.-_':
            system = system.split(c)[0]
        bits = 64 if sys.maxsize > 2**32 else 32
        return system, bits


    def get_url(self, urlmap):
        system, bits = self.get_sysinfo()
        url = urlmap.get(system, None)
        if url is None:
            raise RuntimeError(
                "ERROR: cannot infer the correct url for platform '%s'"
                % (platform,))
        return url


    def parse_args(self, argv):
        if argv and '--insecure' in argv:
            self.insecure = True
            argv.remove('--insecure')
        if argv and '--cacert' in argv:
            i = argv.index('--cacert')
            argv.pop(i)
            self.cacert = argv.pop(i)
        if argv:
            self.fname = argv.pop(0)
        else:
            self.fname = None
        if argv:
            raise RuntimeError("Unrecognized arguments: %s" % (argv,))


    def resolve_filename(self, default):
        if self.fname is None:
            self.fname = PYOMO_CONFIG_DIR
            if not os.path.isdir(self.fname):
                os.makedirs(self.fname)
        if os.path.isdir(self.fname):
            self.fname = os.path.join(self.fname, default)
        targetDir = os.path.dirname(self.fname)
        if not os.path.isdir(targetDir):
            os.makedirs(targetDir)

    def retrieve_url(self, url):
        """Return the contents of a URL as an io.BytesIO object"""
        try:
            ctx = ssl.create_default_context(cafile=self.cacert)
            if self.insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            fetch = urlopen(url, context=ctx)
        except AttributeError:
            # Revert to pre-2.7.9 syntax
            fetch = urlopen(url)
        ans = fetch.read()
        logger.info("  ...downloaded %s bytes" % (len(ans),))
        return ans


    def get_binary_file(self, url):
        with open(self.fname, 'wb') as FILE:
            raw_file = self.retrieve_url(url)
            FILE.write(raw_file)
            logger.info("  ...wrote %s bytes" % (len(raw_file),))


    def get_binary_file_from_zip_archive(self, url, srcname):
        with open(self.fname, 'wb') as FILE:
            zipped_file = io.BytesIO(self.retrieve_url(url))
            raw_file = zipfile.ZipFile(zipped_file).open(srcname).read()
            FILE.write(raw_file)
            logger.info("  ...wrote %s bytes" % (len(raw_file),))


    def get_gzipped_binary_file(self, url):
        with open(self.fname, 'wb') as FILE:
            gzipped_file = io.BytesIO(self.retrieve_url(url))
            raw_file = gzip.GzipFile(fileobj=gzipped_file).read()
            FILE.write(raw_file)
            logger.info("  ...wrote %s bytes" % (len(raw_file),))

