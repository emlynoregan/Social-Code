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
    dependson = db.StringListProperty()
    dependedonby = db.StringListProperty()

    def AddSelfToDependsOns(self):
        for ldependedonfunction in self.GetDependsOn:   
            if not ldependedonfunction.dependedonby:
                ldependedonfunction.dependedonby = []
            if not self.name in ldependedonfunction.dependedonby:
                ldependedonfunction.dependedonby.append(self.name)
                if self.key() == ldependedonfunction.key():
                    self.dependedonby = ldependedonfunction.dependedonby
                ldependedonfunction.put()
        
    def RemoveSelfFromDependsOns(self):
        for ldependedonfunction in self.GetDependsOn:   
            if ldependedonfunction.dependedonby:
                if self.name in ldependedonfunction.dependedonby:
                    ldependedonfunction.dependedonby.remove(self.name)
                    if self.key() == ldependedonfunction.key():
                        self.dependedonby = ldependedonfunction.dependedonby
                    ldependedonfunction.put()

    def calcput(self):
        # should do something smarter with just removing what needs removing
        self.RemoveSelfFromDependsOns()

        if self.name:
            self.searchname = self.name.upper()
        ldependson = self.GetDependsOnFromInput(self.tests)
        ldependson.extend(self.GetDependsOnFromInput(self.code))
        
        self.dependson = ldependson
        self.put()

        self.AddSelfToDependsOns()

    def calcdelete(self):
        self.RemoveSelfFromDependsOns()
        
        for lfunctionrun in self.Runs():
            lfunctionrun.calcdelete()
               
        self.delete()
        
    @classmethod
    def GetOrCreate(cls, aName, aUser):
        retval = cls.GetByName(aName)
        if not retval:
            retval = cls(name = aName, creator = aUser, lastupdatedby = aUser)
            retval.calcput()
        return retval
    
    @classmethod 
    def GetByName(cls, aName):
        retval = None
        if aName:
            retval = cls.all().filter("searchname =", aName.upper()).get()
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
    
    def CheckDependencies(self):
        for ldependsOn in self.GetDependsOn:
            if ldependsOn.key() != self.key():
                llatestRun = ldependsOn.LatestRun
                if llatestRun:
                    if not llatestRun.success:
                        raise Exception("Import '%s' fails: %s" % (ldependsOn.name, llatestRun.errormessage))
                else:
                    raise Exception("Import '%s' has never been run." % (ldependsOn.name))
    
    @property
    def GetDependsOn(self):
        retval = []
        for ldependsonname in self.dependson:
            ldependsOnFunction = Function.all().filter("searchname =", ldependsonname.upper()).get()
            if ldependsOnFunction:
                retval.append(ldependsOnFunction)
        return retval
        
    @property
    def GetDependedOnBy(self):
        retval = []
        for ldependedonbyname in self.dependedonby:
            ldependedOnByFunction = Function.all().filter("searchname =", ldependedonbyname.upper()).get()
            if ldependedOnByFunction:
                retval.append(ldependedOnByFunction)
        return retval
        
    def AddDependsOnToDictionary(self, aDictionary):
        for ldependson in self.GetDependsOn:
            if ldependson.key() != self.key():
                if not ldependson.searchname in aDictionary:
                    aDictionary[ldependson.searchname] = ldependson
                    aDictionary = ldependson.AddDependsOnToDictionary(aDictionary)
        return aDictionary
    
    def GetDependsOnCode(self, aDictionary):
        retval = ""
        for lkey in aDictionary:
            ldependson = aDictionary[lkey]
            if ldependson.code:
                retval += "\n\n" + ldependson.code
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

            self.CheckDependencies()
            
            limportsDict = self.AddDependsOnToDictionary({})

            if limportsDict:
                limportsCode = self.GetDependsOnCode(limportsDict)
            
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
    def GetDependsOnFromInput(cls, aInput):
        if aInput:
            ldependson = re.findall("{{(.*?)}}", aInput)
        else:
            ldependson = []
        return ldependson
    
class FunctionRun(polymodel.PolyModel):
    function = db.ReferenceProperty(Function)
    initiator = db.UserProperty()
    initiated = db.DateTimeProperty(auto_now_add = True)
    success = db.BooleanProperty()
    errormessage = db.StringProperty()

    def calcdelete(self):
        for litem in self.LogItems:
            litem.calcdelete()
        
        self.delete()

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
    
    def calcdelete(self):
        self.delete()
    