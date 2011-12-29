import os
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from datamodel import Function
from google.appengine.ext import db

class FunctionPage(webapp.RequestHandler):

    def get(self):
        
        user = users.get_current_user()

        lsignedIn = False
        lnickname = None
        llogouturl = None
        
        lfunction = None
        lid = self.request.get("id", None)
        if lid:
            lfunction = Function.get_by_id(int(lid))
        
        if not lfunction or not user:
            self.redirect("/")
        else:
            lsignedIn = True
            lnickname = user.nickname()
            llogouturl = users.create_logout_url(self.request.url)
                            
            template_values = {}
            template_values['signedin'] = lsignedIn
            template_values['nickname'] = lnickname
            template_values['logouturl'] = llogouturl        
            template_values['function'] = lfunction
            template_values['functionruns'] = lfunction.Runs().fetch(20, 0)
                    
            path = os.path.join(os.path.dirname(__file__), "functionpage.html")
            self.response.out.write(template.render(path, template_values))
        
    def post(self):
        
        user = users.get_current_user()

        if user:
            lfunction = None
            lid = self.request.get("id", None)
            if lid:
                lfunction = Function.get_by_id(int(lid))
                
            if lfunction:
                    
                lsubject = self.request.get("subject", None)
                
                if lsubject == "Rename Function":
                    lnewName = self.request.get("functionnamebox", None)
                    if lnewName and not Function.NameExists(lnewName):
                        lfunction.name = lnewName
                        lfunction.lastupdatedby = user
                        lfunction.calcput()
                elif lsubject == "Save and Run!":
                    # stub
                    lfunction.code = self.request.get("functioncode")
                    lfunction.tests = self.request.get("functiontests")
                    lfunction.calcput()
                    lfunction.RunTests(user)
                elif lsubject == "Delete":
                    db.delete(lfunction)
                
        self.redirect(self.request.url)
            