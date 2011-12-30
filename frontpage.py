import os
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import users
from datamodel import Function
import util

class FrontPage(webapp.RequestHandler):

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
            
        lerr = self.request.get("err", None)
        
        lsearch = self.request.get("search", "")
            
        lfunctions = Function.GetFunctions(lsearch).fetch(20, 0)
            
        template_values = {}
        template_values['signedin'] = lsignedIn
        template_values['nickname'] = lnickname
        template_values['logouturl'] = llogouturl        
        template_values['loginurl'] = lloginurl
        template_values['search'] = lsearch
        template_values['functions'] = lfunctions
        template_values['err'] = lerr
                
        path = os.path.join(os.path.dirname(__file__), "frontpage.html")
        self.response.out.write(template.render(path, template_values))
        
    def post(self):
        
        user = users.get_current_user()

        lfinishurl = self.request.url
        
        try:
            lsubject = self.request.get("subject", None)
            
            if lsubject == "Add New Function":
                lnewFunctionName = self.request.get("newfunctionname", None)
                if not lnewFunctionName:
                    raise Exception("You must enter a function name")
                
                lnewFunctionName = lnewFunctionName.strip()
                Function.CreateNew(lnewFunctionName, user)
                lfinishurl = util.ClearQueryString(lfinishurl)
                lfinishurl = util.SetQueryStringArg(lfinishurl, "search", lnewFunctionName)
            elif lsubject == "Search":
                lsearchtext = self.request.get("functionnamesearch", None)
                if lsearchtext:
                    lfinishurl = util.SetQueryStringArg(lfinishurl, "search", lsearchtext)
                else:
                    lfinishurl = util.ClearQueryString(lfinishurl)
            elif lsubject == "Clear":
                lfinishurl = util.ClearQueryString(lfinishurl)
        except Exception, ex:
            lfinishurl = util.SetQueryStringArg(lfinishurl, "err", str(ex))
                
        self.redirect(lfinishurl)
            