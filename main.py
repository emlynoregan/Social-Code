import webapp2

from frontpage import FrontPage
from functionpage import FunctionPage

app = webapp2.WSGIApplication([
                            ('/', FrontPage),
                            ('/frontpage', FrontPage),
                            ('/function', FunctionPage)
                            ],
                            debug=True)
