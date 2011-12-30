import os
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from datamodel import Function
from google.appengine.ext import db
import util

class FunctionPage(webapp.RequestHandler):

    def get(self):
        
        user = users.get_current_user()

        lsignedIn = False
        lnickname = None
        llogouturl = None
        lloginurl = None
        if user:
            lsignedIn = True
            lnickname = user.nickname()
            llogouturl = users.create_logout_url(self.request.url)
            
        else:
            lloginurl = users.create_login_url(self.request.url)
        
        lfunction = None
        lid = self.request.get("id", None)
        if lid:
            lfunction = Function.get_by_id(int(lid))
        
        if not lfunction:
            self.redirect("/")
        else:
                            
            template_values = {}
            template_values['signedin'] = lsignedIn
            template_values['nickname'] = lnickname
            template_values['logouturl'] = llogouturl        
            template_values['loginurl'] = lloginurl
            template_values['function'] = lfunction
            template_values['functionruns'] = lfunction.Runs().fetch(20, 0)
                    
            path = os.path.join(os.path.dirname(__file__), "functionpage.html")
            self.response.out.write(template.render(path, template_values))
        
    def post(self):
        user = users.get_current_user()

        lfinishurl = self.request.url
        
        try:
            lfunction = None
            lid = self.request.get("id", None)
            if lid:
                lfunction = Function.get_by_id(int(lid))
                
            if lfunction:
                lsubject = self.request.get("subject", None)
                
                if lsubject == "Save and Run!":
                    lfunction.code = self.request.get("functioncode")
                    lfunction.tests = self.request.get("functiontests")
                    lfunction.calcput()
                    lfunction.RunTests(user)
                elif lsubject == "Delete":
                    db.delete(lfunction)
                    lfinishurl = "/"
                    lfinishurl = util.SetQueryStringArg(lfinishurl, "err", "Function deleted")
            else:
                raise Exception("No function specified")
                
        except Exception, ex:
            lfinishurl = util.SetQueryStringArg(lfinishurl, "err", str(ex))
                
        self.redirect(lfinishurl)
                        