%global _hardened_build 1
%global with_perftools 0

%if 0%{?fedora} >= 19 || 0%{?rhel} >= 7
%global with_redistrib 1
%else
%global with_redistrib 0
%endif

%if 0%{?fedora} >= 19 || 0%{?rhel} >= 7
%bcond_without systemd
%else
%bcond_with systemd
%endif

%bcond_without tests

Name:              redis32u
Version:           3.2.11
Release:           2.ius%{?dist}
Summary:           A persistent key-value database
%if 0%{?rhel} <= 6
Group:             Applications/Databases
%endif
License:           BSD
URL:               http://redis.io

Source0:           http://download.redis.io/releases/redis-%{version}.tar.gz
Source1:           redis.logrotate
Source2:           redis-sentinel.service
Source3:           redis.service
Source5:           redis-sentinel.init
Source6:           redis.init
Source7:           redis-shutdown
Source8:           redis-limit-systemd
Source9:           redis-limit-init

# To refresh patches:
# tar xf redis-xxx.tar.gz && cd redis-xxx && git init && git add . && git commit -m "%{version} baseline"
# git am %{patches}
# Then refresh your patches
# git format-patch HEAD~<number of expected patches>
# Update configuration for Fedora
Patch0001:         0001-redis-3.2.1-redis-conf.patch
Patch0002:         0002-redis-3.2.0-deps-library-fPIC-performance-tuning.patch
Patch0003:         0003-redis-3.2.5-use-system-jemalloc.patch
# tests/integration/replication-psync.tcl failed on slow machines(GITHUB #1417)
Patch0004:         0004-redis-2.8.18-disable-test-failed-on-slow-machine.patch
# Fix sentinel configuration to use a different log file than redis
Patch0005:         0005-redis-3.2.4-sentinel-configuration-file-fix.patch
# https://github.com/antirez/redis/pull/3491 - man pages
Patch0006:         0006-1st-man-pageis-for-redis-cli-redis-benchmark-redis-c.patch
# https://github.com/antirez/redis/pull/3494 - symlink
Patch0007:         0007-install-redis-check-rdb-as-a-symlink-instead-of-dupl.patch

%if 0%{?with_perftools}
BuildRequires:     gperftools-devel
%else
BuildRequires:     jemalloc-devel
%endif
%if %{with tests}
%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
BuildRequires:     procps-ng
%else
BuildRequires:     procps
%endif
BuildRequires:     tcl
%endif
%{?with_systemd:BuildRequires: systemd}

# Required for redis-shutdown
Requires:          /bin/awk
Requires:          logrotate
Requires(pre):     shadow-utils

%if %{with systemd}
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd
%else
Requires(post):    chkconfig
Requires(preun):   chkconfig
Requires(preun):   initscripts
Requires(postun):  initscripts
%endif

Provides: redis = %{version}-%{release}
Provides: redis%{?_isa} = %{version}-%{release}
Conflicts: redis < %{version}


%description
Redis is an advanced key-value store. It is often referred to as a data
structure server since keys can contain strings, hashes, lists, sets and
sorted sets.

You can run atomic operations on these types, like appending to a string;
incrementing the value in a hash; pushing to a list; computing set 
intersection, union and difference; or getting the member with highest 
ranking in a sorted set.

In order to achieve its outstanding performance, Redis works with an 
in-memory dataset. Depending on your use case, you can persist it either 
by dumping the dataset to disk every once in a while, or by appending 
each command to a log.

Redis also supports trivial-to-setup master-slave replication, with very 
fast non-blocking first synchronization, auto-reconnection on net split 
and so forth.

Other features include Transactions, Pub/Sub, Lua scripting, Keys with a 
limited time-to-live, and configuration settings to make Redis behave like 
a cache.

You can use Redis from most programming languages also.

%if 0%{?with_redistrib}
%package           trib
Summary:           Cluster management script for Redis
BuildArch:         noarch
Requires:          ruby
Requires:          rubygem-redis

%description       trib
Redis cluster management utility providing cluster creation, node addition
and removal, status checks, resharding, rebalancing, and other operations.
%endif

%prep
%setup -q -n redis-%{version}
rm -frv deps/jemalloc
%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
%patch0004 -p1
%patch0005 -p1
%patch0006 -p1
%patch0007 -p1

# No hidden build.
sed -i -e 's|\t@|\t|g' deps/lua/src/Makefile
sed -i -e 's|$(QUIET_CC)||g' src/Makefile
sed -i -e 's|$(QUIET_LINK)||g' src/Makefile
sed -i -e 's|$(QUIET_INSTALL)||g' src/Makefile
# Ensure deps are built with proper flags
sed -i -e 's|$(CFLAGS)|%{optflags}|g' deps/Makefile
sed -i -e 's|OPTIMIZATION?=-O3|OPTIMIZATION=%{optflags}|g' deps/hiredis/Makefile
sed -i -e 's|$(LDFLAGS)|%{?__global_ldflags}|g' deps/hiredis/Makefile
sed -i -e 's|$(CFLAGS)|%{optflags}|g' deps/linenoise/Makefile
sed -i -e 's|$(LDFLAGS)|%{?__global_ldflags}|g' deps/linenoise/Makefile

%build
make %{?_smp_mflags} \
    DEBUG="" \
    LDFLAGS="%{?__global_ldflags}" \
    CFLAGS+="%{optflags}" \
    LUA_LDFLAGS+="%{?__global_ldflags}" \
%if 0%{?with_perftools}
    MALLOC=tcmalloc \
%else
    MALLOC=jemalloc \
%endif
    all

%install
make install INSTALL="install -p" PREFIX=%{buildroot}%{_prefix}

# Filesystem.
install -d %{buildroot}%{_sharedstatedir}/redis
install -d %{buildroot}%{_localstatedir}/log/redis
install -d %{buildroot}%{_localstatedir}/run/redis

# Install logrotate file.
install -pDm644 %{S:1} %{buildroot}%{_sysconfdir}/logrotate.d/redis

# Install configuration files.
install -pDm640 redis.conf %{buildroot}%{_sysconfdir}/redis.conf
install -pDm640 sentinel.conf %{buildroot}%{_sysconfdir}/redis-sentinel.conf

%if %{with systemd}
# Install Systemd unit files.
mkdir -p %{buildroot}%{_unitdir}
install -pm644 %{S:3} %{buildroot}%{_unitdir}
install -pm644 %{S:2} %{buildroot}%{_unitdir}
# Install systemd limit files (requires systemd >= 204)
install -p -D -m 644 %{S:8} %{buildroot}%{_sysconfdir}/systemd/system/redis.service.d/limit.conf
install -p -D -m 644 %{S:8} %{buildroot}%{_sysconfdir}/systemd/system/redis-sentinel.service.d/limit.conf
%else
# Install SysV service files.
install -pDm755 %{S:5} %{buildroot}%{_initrddir}/redis-sentinel
install -pDm755 %{S:6} %{buildroot}%{_initrddir}/redis
install -p -D -m 644 %{S:9} %{buildroot}%{_sysconfdir}/security/limits.d/95-redis.conf
%endif

# Fix non-standard-executable-perm error.
chmod 755 %{buildroot}%{_bindir}/redis-*

# Install redis-shutdown
install -pDm755 %{S:7} %{buildroot}%{_libexecdir}/redis-shutdown

%if 0%{?with_redistrib}
# Install redis-trib
install -pDm755 src/redis-trib.rb %{buildroot}%{_bindir}/redis-trib
%endif

# Install man pages
man=$(dirname %{buildroot}%{_mandir})
for page in man/man?/*; do
    install -Dpm644 $page $man/$page
done
ln -s redis-server.1 %{buildroot}%{_mandir}/man1/redis-sentinel.1
ln -s redis.conf.5   %{buildroot}%{_mandir}/man5/redis-sentinel.conf.5


%check
%if 0%{?with_tests}
make test
make test-sentinel
%endif


%pre
getent group redis &> /dev/null || \
groupadd -r redis &> /dev/null
getent passwd redis &> /dev/null || \
useradd -r -g redis -d %{_sharedstatedir}/redis -s /sbin/nologin \
-c 'Redis Database Server' redis &> /dev/null
exit 0


%post
%if %{with systemd}
%systemd_post redis.service
%systemd_post redis-sentinel.service
%else
if [ $1 -eq 1 ]; then
    chkconfig --add redis &> /dev/null || :
    chkconfig --add redis-sentinel &> /dev/null || :
fi
%endif


%preun
%if %{with systemd}
%systemd_preun redis.service
%systemd_preun redis-sentinel.service
%else
if [ $1 -eq 0 ]; then
    service redis stop &> /dev/null || :
    chkconfig --del redis &> /dev/null || :
    service redis-sentinel stop &> /dev/null || :
    chkconfig --del redis-sentinel &> /dev/null || :
fi
%endif


%postun
%if %{with systemd}
%systemd_postun_with_restart redis.service
%systemd_postun_with_restart redis-sentinel.service
%else
if [ $1 -ge 1 ]; then
    service redis condrestart &> /dev/null || :
    service redis-sentinel condrestart &> /dev/null || :
fi
%endif


%files
%license COPYING
%doc 00-RELEASENOTES BUGS CONTRIBUTING MANIFESTO README.md
%config(noreplace) %{_sysconfdir}/logrotate.d/redis
%attr(0640, redis, root) %config(noreplace) %{_sysconfdir}/redis.conf
%attr(0640, redis, root) %config(noreplace) %{_sysconfdir}/redis-sentinel.conf
%dir %attr(0750, redis, redis) %{_sharedstatedir}/redis
%dir %attr(0750, redis, redis) %{_localstatedir}/log/redis
%dir %attr(0750, redis, redis) %ghost %{_localstatedir}/run/redis
%if 0%{?with_redistrib}
%exclude %{_bindir}/redis-trib
%endif
%{_bindir}/redis-*
%{_libexecdir}/redis-*
%{_mandir}/man1/redis*
%{_mandir}/man5/redis*
%if %{with systemd}
%{_unitdir}/redis.service
%{_unitdir}/redis-sentinel.service
%dir %{_sysconfdir}/systemd/system/redis.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/redis.service.d/limit.conf
%dir %{_sysconfdir}/systemd/system/redis-sentinel.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/redis-sentinel.service.d/limit.conf
%else
%{_initrddir}/redis
%{_initrddir}/redis-sentinel
%config(noreplace) %{_sysconfdir}/security/limits.d/95-redis.conf
%endif

%if 0%{?with_redistrib}
%files trib
%license COPYING
%{_bindir}/redis-trib
%endif

%changelog
* Thu Nov 09 2017 Ben Harper <ben.harper@rackspace.com> - 3.2.11-2.ius
- correct name to redis-trib

* Thu Sep 21 2017 Ben Harper <ben.harper@rackspace.com> - 3.2.11-1.ius
- Latest upstream
- add redis-trib from Fedora:
  https://src.fedoraproject.org/rpms/redis/c/64e67eb9fe9855cedb2d74e8c13ba1377a1d3cb
- fix permissions on service files from Fedora:
  https://src.fedoraproject.org/rpms/redis/c/cf49c6bbe92ce9574c73c5fbc45ba42e3bbada7a

* Fri Aug 18 2017 Ben Harper <ben.harper@rackspace.com> - 3.2.10-2.ius
- remove Source4 source from Fedora:
  https://src.fedoraproject.org/rpms/redis/c/cf49c6bbe92ce9574c73c5fbc45ba42e3bbada7a?branch=master

* Fri Jul 28 2017 Carl George <carl@george.computer> - 3.2.10-1.ius
- Latest upstream
- Move redis-shutdown to libexec (Fedora)
- Add missing man pages #1374577 https://github.com/antirez/redis/pull/3491 (Fedora)
- Provide redis-check-rdb as a symlink to redis-server #1374736 https://github.com/antirez/redis/pull/3494 (Fedora)
- Data and configuration should not be publicly readable #1374700 (Fedora)
- Fix a shutdown failure with Unix domain sockets (RHBZ #1444988) (Fedora)
- Add RuntimeDirectory=redis to systemd unit file (RHBZ #1454700) (Fedora)
- Mark rundir as %ghost since it may disappear (tmpfs - #1454700) (Fedora)

* Wed May 17 2017 Ben Harper <ben.harper@rackspace.com> - 3.2.9-1.ius
- Latest upstream

* Mon Feb 13 2017 Ben Harper <ben.harper@rackspace.com> - 3.2.8-1.ius
- Latest upstream

* Tue Jan 31 2017 Ben Harper <ben.harper@rackspace.com> - 3.2.7-1.ius
- Latest upstream

* Tue Dec 06 2016 Ben Harper <ben.harper@rackspace.com> - 3.2.6-1.ius
- Latest upstream

* Thu Oct 27 2016 Carl George <carl.george@rackspace.com> - 3.2.5-1.ius
- Latest upstream
- Refresh Patch0003

* Mon Sep 26 2016 Carl George <carl.george@rackspace.com> - 3.2.4-1.ius
- Latest upstream

* Fri Aug 05 2016 Carl George <carl.george@rackspace.com> - 3.2.3-1.ius
- Latest upstream

* Fri Jul 29 2016 Ben Harper <ben.harper@rackspace.com> - 3.2.2-1.ius
- Latest upstream

* Fri Jun 17 2016 Carl George <carl.george@rackspace.com> - 3.2.1-1.ius
- Latest upstream
- Refresh Patch1
- Only run `chkconfig --add` on initial install
- Ensure scriptlets have 0 exit status

* Fri Jun 03 2016 Carl George <carl.george@rackspace.com> - 3.2.0-1.ius
- Upstream 3.2.0
- Port from Fedora to IUS
- Rebase Patch0001 and Patch0002
- Use either procps or procps-ng as appropriate
- Enable test suite

* Mon Feb  8 2016 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.6-3
- Fix redis-shutdown to handle password-protected instances shutdown

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 3.0.6-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Sat Dec 19 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.6-1
- Upstream 3.0.6 (RHBZ#1272281)

* Fri Oct 16 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.5-1
- Upstream 3.0.5
- Fix slave/master replication hanging forever in certain case

* Mon Sep 07 2015 Christopher Meng <rpm@cicku.me> - 3.0.4-1
- Update to 3.0.4

* Sun Aug 30 2015 Christopher Meng <rpm@cicku.me> - 3.0.3-2
- Rebuilt for jemalloc 4.0.0

* Tue Jul 21 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.3-1
- Upstream 3.0.3

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.0.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Thu Jun 04 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.2-1
- Upstream 3.0.2 (RHBZ #1228245)
- Fix Lua sandbox escape and arbitrary code execution (RHBZ #1228331)

* Sat May 09 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.1-1
- Upstream 3.0.1 (RHBZ #1208322)

* Tue Apr 14 2015 Remi Collet <remi@fedoraproject.org> - 3.0.0-2
- rotate /var/log/redis/sentinel.log

* Thu Apr  2 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.0-1
- Upstream 3.0.0 (RHBZ #1208322)

* Thu Mar 26 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.19-2
- Fix redis-shutdown on multiple NIC setup (RHBZ #1201237)

* Fri Feb 27 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.19-1
- Upstream 2.8.19 (RHBZ #1175232)
- Fix permissions for tmpfiles (RHBZ #1182913)
- Add limits config files
- Spec cleanups

* Fri Dec 05 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.18-1
- Upstream 2.8.18
- Rebased patches

* Sat Sep 20 2014 Remi Collet <remi@fedoraproject.org> - 2.8.17-1
- Upstream 2.8.17
- fix redis-sentinel service unit file for systemd
- fix redis-shutdown for sentinel
- also use redis-shutdown in init scripts

* Wed Sep 17 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.15-2
- Minor fix to redis-shutdown (from Remi Collet)

* Sat Sep 13 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.15-1
- Upstream 2.8.15 (critical bugfix for sentinel)
- Fix to sentinel systemd service and configuration (thanks Remi)
- Refresh patch management

* Thu Sep 11 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.14-2
- Cleanup spec
- Fix shutdown for redis-{server,sentinel}
- Backport fixes from Remi Collet repository (ie: sentinel working)

* Thu Sep 11 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.14-1
- Upstream 2.8.14 (RHBZ #1136287)
- Bugfix for lua scripting users (server crash)
- Refresh patches
- backport spec from EPEL7 (thanks Warren)

* Wed Jul 16 2014 Christopher Meng <rpm@cicku.me> - 2.8.13-1
- Update to 2.8.13

* Tue Jun 24 2014 Christopher Meng <rpm@cicku.me> - 2.8.12-1
- Update to 2.8.12

* Wed Jun 18 2014 Christopher Meng <rpm@cicku.me> - 2.8.11-1
- Update to 2.8.11

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.16-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri Sep 06 2013 Fabian Deutsch <fabian.deutsch@gmx.de> - 2.6.16-1
- Update to 2.6.16
- Fix rhbz#973151
- Fix rhbz#656683
- Fix rhbz#977357 (Jan Vcelak <jvcelak@fedoraproject.org>)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.13-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 23 2013 Peter Robinson <pbrobinson@fedoraproject.org> 2.6.13-4
- ARM has gperftools

* Wed Jun 19 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-3
- Modify jemalloc patch for s390 compatibility (Thanks sharkcz)

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-2
- Unbundle jemalloc

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-1
- Add compile PIE flag (rhbz#955459)
- Update to redis 2.6.13 (rhbz#820919)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Dec 27 2012 Silas Sewell <silas@sewell.org> - 2.6.7-1
- Update to redis 2.6.7

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.4.15-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-2
- Remove TODO from docs

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-1
- Update to redis 2.4.15

* Sat May 19 2012 Silas Sewell <silas@sewell.org> - 2.4.13-1
- Update to redis 2.4.13

* Sat Mar 31 2012 Silas Sewell <silas@sewell.org> - 2.4.10-1
- Update to redis 2.4.10

* Fri Feb 24 2012 Silas Sewell <silas@sewell.org> - 2.4.8-1
- Update to redis 2.4.8

* Sat Feb 04 2012 Silas Sewell <silas@sewell.org> - 2.4.7-1
- Update to redis 2.4.7

* Wed Feb 01 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-4
- Fixed a typo in the spec

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-3
- Fix .service file, to match config (Type=simple).

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-2
- Fix .service file, credits go to Timon.

* Thu Jan 12 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-1
- Update to 2.4.6
- systemd unit file added
- Compiler flags changed to compile 2.4.6
- Remove doc/ and Changelog

* Sun Jul 24 2011 Silas Sewell <silas@sewell.org> - 2.2.12-1
- Update to redis 2.2.12

* Fri May 06 2011 Dan Horák <dan[at]danny.cz> - 2.2.5-2
- google-perftools exists only on selected architectures

* Sat Apr 23 2011 Silas Sewell <silas@sewell.ch> - 2.2.5-1
- Update to redis 2.2.5

* Sat Mar 26 2011 Silas Sewell <silas@sewell.ch> - 2.2.2-1
- Update to redis 2.2.2

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.4-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sun Dec 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.4-1
- Update to redis 2.0.4

* Tue Oct 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.3-1
- Update to redis 2.0.3

* Fri Oct 08 2010 Silas Sewell <silas@sewell.ch> - 2.0.2-1
- Update to redis 2.0.2
- Disable checks section for el5

* Sat Sep 11 2010 Silas Sewell <silas@sewell.ch> - 2.0.1-1
- Update to redis 2.0.1

* Sat Sep 04 2010 Silas Sewell <silas@sewell.ch> - 2.0.0-1
- Update to redis 2.0.0

* Thu Sep 02 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-3
- Add Fedora build flags
- Send all scriplet output to /dev/null
- Remove debugging flags
- Add redis.conf check to init script

* Mon Aug 16 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-2
- Don't compress man pages
- Use patch to fix redis.conf

* Tue Jul 06 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-1
- Initial package
