import urlparse
import cgi
import urllib 

def SetQueryStringArg(aUrl, aKey, aValue):
    lurlParts = urlparse.urlparse(aUrl)
    if (lurlParts and lurlParts[4]):
        lqlist = cgi.parse_qsl(lurlParts[4])
    else:
        lqlist = []
        
    lqdict = {}
    for litem in lqlist:
        lqdict[litem[0]] = litem[1]

    lqdict[aKey] = aValue

    lqlist = []
    for lkey in lqdict:
        lqlist.append((lkey, lqdict[lkey]))
        
    lqstr = urllib.urlencode(lqlist)
    lnewUrl = urlparse.urlunparse((lurlParts[0],lurlParts[1],lurlParts[2], lurlParts[3], lqstr, lurlParts[5]))
    
    return lnewUrl

def ClearQueryString(aUrl):
    lurlParts = urlparse.urlparse(aUrl)
    lnewUrl = urlparse.urlunparse((lurlParts[0],lurlParts[1],lurlParts[2], lurlParts[3], urllib.urlencode([]), lurlParts[5]))
    
    return lnewUrl
