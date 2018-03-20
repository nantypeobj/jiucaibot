# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 16:33:15 2017

@author: Administrator
"""

#REST

#template:
def form_url(path,path_arg=None, parameters=None,version='v2'):
        # build the basic url
        url = "%s/%s/%s" % (self.server,version,path)

        # If there is a path_arh, interpolate it into the URL.
        # In this case the path that was provided will need to have string
        # interpolation characters in it, such as PATH_TICKER
        if path_arg:
            url = url % (path_arg)

        # Append any parameters to the URL.
        if parameters:
            url = "%s?%s" % (url, self._build_parameters(parameters))
        return url
