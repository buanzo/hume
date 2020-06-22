TL;DR: Add hume commands inside your scripts to better report to a central
location.  Currently supporting Slack, syslog, remote-syslog, logstash, etc

Imagine this: You have some cron scripts.  They need to run correctly, and
you need to know if anything happens.  You usually check logs via email or
some cool dashboard.  Yeah.  But it gets boring, repetitive and you end up
not checking the logs.  It is a well known sysadmin syndrome.

Hume client works and can be used in bash scripts, or during a screen
session, to provide real time updates to your managers, customers, etc.

So, for instance write those scripts adding hume commands in them:
