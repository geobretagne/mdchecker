#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mdchecker.inspirobot import Inspirobot
import re

class MdUnitTestSpatial(Inspirobot.MdUnitTest):
    """check spatial descriptors"""
    def set(self):
        self.name=u'GEO'
        self.abstract=u"""Descripteurs spatiaux. Vérifie si une résolution est fournie."""
        self.xpath = {
        }
        
    def test(self, md):
        pass
