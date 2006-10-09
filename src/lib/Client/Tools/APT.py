'''This is the bcfg2 support for apt-get'''
__revision__ = '$Revision$'

import apt_pkg, os, re
import Bcfg2.Client.Tools

class APT(Bcfg2.Client.Tools.PkgTool):
    '''The Debian toolset implements package and service operations and inherits
    the rest from Toolset.Toolset'''
    __name__ = 'APT'
    __execs__ = ['/usr/bin/debsums', '/usr/bin/apt-get', '/usr/bin/dpkg']
    __important__ = ["/etc/apt/sources.list", "/var/cache/debconf/config.dat", \
                     "/var/cache/debconf/templates.dat", '/etc/passwd', '/etc/group', \
                     '/etc/apt/apt.conf', '/etc/dpkg/dpkg.cfg']
    __handles__ = [('Package', 'deb')]
    __req__ = {'Package': ['name', 'version']}
    pkgtype = 'deb'
    pkgtool = ('apt-get --reinstall -q=2 --force-yes -y install %s',
               ('%s=%s', ['name', 'version']))
    
    svcre = re.compile("/etc/.*/[SK]\d\d(?P<name>\S+)")

    def __init__(self, logger, cfg, setup, states):
        Bcfg2.Client.Tools.PkgTool.__init__(self, logger, cfg, setup, states)
        self.cfg = cfg
        os.environ["DEBIAN_FRONTEND"] = 'noninteractive'
        if not self.setup['dryrun']:
            if self.setup['kevlar']:
                self.cmd.run("dpkg --force-confold --configure --pending")
                self.cmd.run("apt-get clean")
                self.cmd.run("apt-get -q=2 -y update")
        self.installed = {}
        self.RefreshPackages()

    def RefreshPackages(self):
        '''Refresh memory hashes of packages'''
        apt_pkg.init()
        cache = apt_pkg.GetCache()
        self.installed = {}
        for pkg in cache.Packages:
            if pkg.CurrentVer:
                self.installed[pkg.Name] = pkg.CurrentVer.VerStr

    def VerifyPackage(self, entry, modlist):
        '''Verify package for entry'''
        if not entry.attrib.has_key('version'):
            self.logger.info("Cannot verify unversioned package %s" %
                             (entry.attrib['name']))
            return False
        if self.installed.has_key(entry.attrib['name']):
            if self.installed[entry.attrib['name']] == entry.attrib['version']:
                if not self.setup['quick'] and entry.get('verify', 'true') == 'true':
                    output = self.cmd.run("/usr/bin/debsums -s %s" % entry.get('name'))[1]
                    if [filename for filename in output if filename not in modlist]:
                        return False
                return True
            else:
                entry.set('current_version', self.installed[entry.get('name')])
                return False
        entry.set('current_exists', 'false')
        return False

    def RemovePackages(self, packages):
        '''Deal with extra configuration detected'''
        if len(packages) > 0:
            self.logger.info('Removing packages:')
            self.logger.info(packages)
            self.cmd.run("apt-get remove -y --force-yes %s" % \
                         " ".join(packages))
            self.RefreshPackages()
            self.extra = self.FindExtraPackages()
              
        