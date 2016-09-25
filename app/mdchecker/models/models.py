from mdchecker.main import db
from sqlalchemy import func


class ResourceMd(db.Model):
    """ResourceMd represents the metadata of a resource stored in a catalog
    """
    __tablename__ = 'resource_md'
    id = db.Column(db.Integer, primary_key=True)
    cat_url = db.Column(db.String(512))
    file_id = db.Column(db.String(128))
    md_date = db.Column(db.DateTime)
    res_date = db.Column(db.DateTime)
    res_uri = db.Column(db.String(128))
    res_title = db.Column(db.String(128))
    res_abstract = db.Column(db.String(1024))
    res_organisation_name = db.Column(db.String(128))

    def __init__(self, *args, **kwargs):
        super(ResourceMd, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<ResourceMd: {0}>".format(self.id)


class TestSession(db.Model):
    """TestSession represents a session of tests
    """
    __tablename__ = 'test_session'
    id = db.Column(db.Integer, primary_key=True)
    cat_url = db.Column(db.String(512))
    filter = db.Column(db.String(1024))
    date = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super(TestSession, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<TestSession: {0}>".format(self.id)

    def get_nb_md_tested(self):
        return self.md_reports.count()

    def get_average_md_score(self):
        return self.md_reports.with_entities(func.avg(MdReport.score).label('average_score')).first()[0]

    def get_percentage_md_upper_than_80(self):
        total_md = self.get_nb_md_tested()
        if total_md == 0:
            return 0
        nb_md = self.md_reports.filter(MdReport.score > 80).count()
        return nb_md*100/total_md

    def get_percentage_md_lower_than_20(self):
        total_md = self.get_nb_md_tested()
        if total_md == 0:
            return 0
        nb_md = self.md_reports.filter(MdReport.score < 20).count()
        return nb_md*100/total_md

    def get_filter_as_dict(self):
        """
        Get a dictionary containing the content of the self.filter string
        Only not None and not empty strings are put in the dictionary

        @return:    a dictionary
        """
        filter_items = self.filter.split("&")
        filter_items = [filter_item.strip() for filter_item in filter_items if len(filter_item.strip()) != 0]

        dict = {}
        for filter_item in filter_items:
            key, value = filter_item.split("=")

            if key and key.strip() and value and value.strip():
                dict[key.strip()] = value.strip()
        return dict

class MdReport(db.Model):
    """MdReport represents a test report run on 1 resource metadata
    1 MdReport instance is linked to 1 TestSession instance and 1 ResourceMd instance
    1 MdReport instance is linked to many UnitTestResult instances
     """
    __tablename__ = 'md_report'
    id = db.Column(db.Integer, primary_key=True)
    test_session_id = db.Column(db.Integer, db.ForeignKey('test_session.id'))
    test_session = db.relationship('TestSession', backref=db.backref('md_reports', lazy='dynamic'))
    md_id = db.Column(db.Integer, db.ForeignKey('resource_md.id'))
    md = db.relationship('ResourceMd', backref=db.backref('resource_md', lazy='dynamic'))
    score = db.Column(db.Integer)

    def __init__(self, *args, **kwargs):
        super(MdReport, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<MdReport: {0}>".format(self.id)


class UnitTestResult(db.Model):
    """UnitTestResult represents 1 result of a test on a specific resource metadata
    """
    __tablename__ = 'unit_test_result'
    id = db.Column(db.Integer, primary_key=True)
    md_report_id = db.Column(db.Integer, db.ForeignKey('md_report.id'))
    md_report = db.relationship('MdReport', backref=db.backref('unit_test_results', lazy='dynamic'))
    test_name = db.Column(db.String(16))
    test_abstract = db.Column(db.String(256))
    test_result_level = db.Column(db.String(16))
    test_result_text = db.Column(db.String(1024))

    def __init__(self, *args, **kwargs):
        super(UnitTestResult, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<UnitTestResult: {0}>".format(self.id)
