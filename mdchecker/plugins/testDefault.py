#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot
import re


class MdUnitTestDefault(Inspirobot.MdUnitTest):
    """check default string values"""
    def set(self):
        self.name = u'DEFAULT'
        self.abstract = u"Valeurs par défaut. Teste la présence de valeurs par défaut " \
                        u"des modèles de métadonnées de Geonetwork."
        self.xpath = {}

    def test(self, md):

        rep = Inspirobot.MdUnitTestReport(self.name, self.abstract)

        searched_regex = "^-- "

        nb_default_values = sum([len(re.findall(searched_regex, t)) for t in md.itertext()])
        if nb_default_values > 0:
            rep.addResult('error', u'%s valeurs par défaut trouvées' % nb_default_values)
            self.addReport(rep)
