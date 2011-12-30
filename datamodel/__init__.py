'''
@author: emlyn
'''
from google.appengine.ext import db
from google.appengine.ext.db import polymodel
import random
import math
import re

class Function(polymodel.PolyModel):
    creator = db.UserProperty()
    created = db.DateTimeProperty(auto_now_add = True)
    lastupdatedby = db.UserProperty()
    lastupdated = db.DateTimeProperty(auto_now = True)
    name = db.StringProperty(required=True)
    searchname = db.StringProperty(required=True)
    code = db.TextProperty()
    tests = db.TextProperty()
    imports = db.StringListProperty()

    def calcput(self):
        if self.name:
            self.searchname = self.name.upper()
        limports = self.GetImportsFromInput(self.tests)
        limports.extend(self.GetImportsFromInput(self.code))
        
        self.imports = limports
        
        self.put()
        
    @classmethod
    def GetOrCreate(cls, aName, aUser):
        retval = cls.all().filter("name =", aName).get()
        if not retval:
            retval = cls(name = aName, creator = aUser, lastupdatedby = aUser)
            retval.calcput()
        return retval
    
    @classmethod
    def CreateNew(cls, aName, aUser):
        if cls.NameExists(aName):
            raise Exception("Name already exists")
        else:
#            lname = cls.GenerateName(aUser)
            retval = cls(name = aName, creator = aUser, lastupdatedby = aUser, searchname=aName.upper())
            retval.calcput()
            return retval
    
    @classmethod
    def GetFunctions(cls, aSearch):
        retval = cls.all()
        
        if aSearch:
            lsearch = aSearch.upper()
            retval = retval.filter("searchname >=", lsearch).filter("searchname <", lsearch + "zzzzzzzzzzzzzzzzzzzzzzzzzzz")
        
        retval = retval.order("searchname").order("-created")
        
        return retval
        
    @classmethod
    def GenerateName(cls, aUser):
        retval = None
        lnameExists = None
        while not retval or lnameExists:
            retval = aUser.nickname() + str(int(math.trunc(random.random() * 1000)))
            retval = retval.replace("@", "").replace(".", "")
            lnameExists = cls.NameExists(retval)
        return retval

    @classmethod
    def NameExists(cls, aName):
        lname = aName
        if not lname:
            lname = ""
        lname = lname.upper()
        retval = not cls.all().filter("searchname =", lname).get() is None
        return retval

    @property
    def LatestRun(self):
        return FunctionRun.all().filter("function =", self).order("-initiated").get()
    
    def Runs(self):
        return FunctionRun.all().filter("function =", self).order("-initiated")
    
    def CheckImports(self):
        if self.imports:
            for limportname in self.imports:
                limport = Function.all().filter("searchname =", limportname.upper()).get()
                if limport:
                    llatestRun = limport.LatestRun
                    if llatestRun:
                        if not llatestRun.success:
                            raise Exception("Import '%s' fails: %s" % (limportname, llatestRun.errormessage))
                    else:
                        raise Exception("Import '%s' has never been run." % (limportname))
                else:
                    raise Exception("Import '%s' not found." % (limportname))
    
    @property
    def GetImports(self):
        retval = []
        for limportname in self.imports:
            limport = Function.all().filter("searchname =", limportname.upper()).get()
            if limport:
                retval.append(limport)
        return retval
        
    def AddImportsToDictionary(self, aDictionary):
        for limportname in self.imports:
            if not limportname in aDictionary:
                limport = Function.all().filter("searchname =", limportname.upper()).get()
                if limport:
                    aDictionary[limportname] = limport
                    aDictionary = limport.AddImportsToDictionary(aDictionary)
        return aDictionary
    
    def GetImportsCode(self, aDictionary):
        retval = ""
        for lkey in aDictionary:
            limport = aDictionary[lkey]
            if limport.code:
                retval += "\n\n" + limport.code
        return retval
    
    def RunTests(self, aInitiator):
        lfunctionrun = FunctionRun()
        lfunctionrun.function = self
        lfunctionrun.initiator = aInitiator
        lfunctionrun.put() # temporary, so we can save logitems
        
        try:
            def xlog(aMessage):
                logitem = LogItem()
                logitem.functionrun = lfunctionrun
                logitem.message = aMessage
                logitem.put()

            def xcheck(aBool, aMessage=None):
                if not aBool:
                    if aMessage:
                        raise Exception("Assert failed: %s" % aMessage)
                    else:
                        raise Exception("Assert failed.")
                    
            # "__builtins__":None, 
            lscope = {"__builtins__":None, "log":xlog, "check":xcheck, "str": str}

            self.CheckImports()
            
            limportsDict = self.AddImportsToDictionary({})

            if limportsDict:
                limportsCode = self.GetImportsCode(limportsDict)
            
                try:
                    exec limportsCode in lscope
                except Exception, ex:
                    raise ex.__class__("Imports: %s" % unicode(ex))

            lcode = self.code
            if not lcode:
                lcode = ""
                
            if limportsDict:
                lcode += limportsCode
                
            try:
                exec lcode in lscope
            except Exception, ex:
                raise ex.__class__("Implementation: %s" % unicode(ex))
                
            if self.tests:
                lcode += "\n\n" + self.tests
                
            try:
                exec lcode in lscope
            except Exception, ex:
                raise ex.__class__("Tests: %s" % unicode(ex))
            
            lfunctionrun.success = True
        except Exception, ex:
            lfunctionrun.success = False
            lfunctionrun.errormessage = unicode(ex)
        
        lfunctionrun.put()
    
    @classmethod
    def GetImportsFromInput(cls, aInput):
        if aInput:
            limports = re.findall("{{(.*?)}}", aInput)
        else:
            limports = []
        return limports
    
class FunctionRun(polymodel.PolyModel):
    function = db.ReferenceProperty(Function)
    initiator = db.UserProperty()
    initiated = db.DateTimeProperty(auto_now_add = True)
    success = db.BooleanProperty()
    errormessage = db.StringProperty()

    @property
    def LogItems(self):
        return LogItem.all().filter("functionrun =", self).order("timestamp")

    @property
    def TopLogItems(self):
        return LogItem.all().filter("functionrun =", self).order("timestamp").fetch(20, 0)
    
class LogItem(polymodel.PolyModel):
    functionrun = db.ReferenceProperty(FunctionRun)
    timestamp = db.DateTimeProperty(auto_now_add = True)
    message = db.StringProperty()
    