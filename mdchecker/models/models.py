#db tests
from mdchecker.main import db


class ResourceMd(db.Model):
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
    __tablename__ = 'test_session'
    id = db.Column(db.Integer, primary_key=True)
    cat_url = db.Column(db.String(512))
    filter = db.Column(db.String(1024))
    date = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super(TestSession, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<TestSession: {0}>".format(self.id)


class MdReport(db.Model):
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
    __tablename__ = 'unit_test_result'
    id = db.Column(db.Integer, primary_key=True)
    md_report_id = db.Column(db.Integer, db.ForeignKey('md_report.id'))
    md_report = db.relationship('MdReport', backref=db.backref('unit_test_results', lazy='dynamic'))
    test_id = db.Column(db.String(16))
    test_result_level = db.Column(db.String(16))
    test_result_text = db.Column(db.String(1024))

    def __init__(self, *args, **kwargs):
        super(UnitTestResult, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<UnitTestResult: {0}>".format(self.id)
