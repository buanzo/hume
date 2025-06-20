# hume
Imagine this: You have some cron scripts. They need to run correctly, and you need to know
if anything happens. You usually check logs via email or some cool
dashboard. Yeah. But it gets boring, repetitive and you end up not checking
the logs. It is a well known sysadmin syndrome.

Hume client works and can be used in bash scripts, or during a screen
session, to provide real time updates to your managers, customers, etc.

So, for instance write those scripts adding hume commands in them:

```
#!/bin/bash
# This script updates wordpress core, plugins and themes
# on a number of different directories.
wpcli='/usr/local/bin/wp'

# Maybe hume could read this variables
HTASK="WORDPRESS_UPDATE"
HTAGS="wordpress,cron,updates"

hume -c counter-start -t "$HTASK" -T "$HTAGS" -m "Starting wordpress update cron process"
for dir in "/var/www/site1/htdocs" "/var/www/site2/htdocs" "/var/www/site3/htdocs"
do
	hume -t "$HTASK" -T "$HTAGS" -L info -m "Updating in $dir"
        cd $dir || hume -t "$HTASK" -T "$HTAGS" -L error -m "$dir does not exist"
        $wpcli core update || hume -t "$HTASK" -T "$HTAGS" -L error -m "Core update error in $dir"
        $wpcli plugin update --all || hume -t "$HTASK" -T "$HTAGS" -L error -m "Plugins update error in $dir"
        $wpcli theme update --all || hume -t "$HTASK" -T "$HTAGS" -L error -m "Themes update error in $dir"
	hume -t "$HTASK" -T "$HTAGS" -L info -m "Update process for $dir finished"
done
hume -c counter-stop -t "$HTASK" -T "$HTAGS" -m "Finished wordpress update cron task"
```

The above usage example gives you a general idea that Hume is an agnostic system administration tool/framework.

# Why is Hume agnostic?

Every sysadmin, believe it or not, is a human being.

The same reason there are awesome tools, for example Faraday (used by
penetration testers and other members of the information security community)
allows each individual pentester to do their work using the
tools they like, and still be able to structurally share and enhance the data
that comes out of them in a centralized knowledge database.

Hume is the system administration equivalent of Faraday. And I think it goes
hand in hand with devops, devsecops, etc.

And both are agnostic in relation to how each person does their job: you do
NOT need to use bash even. If you know enough Python, you can import hume
into your script and report directly from your code. TODO: add an example.

# Current Status / Needs

* Query database and query tools (Codename KANT).

Humed works in localhost mode only, but primary/secondary ideas have been
considered (see below) - There is NO QUERY TOOL, but you can get data off
the humed.sqlite3 database

Then you could check the status of the latest run of the task:

```
#!/bin/bash
# echo check status of wordpress_update task for webserver host
humequery -t WORDPRESS_UPDATE --latest --hostname="webserver"
```

And you would get the list of every hume event, plus a summary, including 

* We need a UI/UX designer/developer, maybe a REST API for querytools.


# Slack support

Hume can send messages to Slack using the Incoming Webhooks method. Create
a channel for hume messages, then a Slack App, finally create an incoming
webhook for that channel and paste the webhook url into the humed
configuration file.

Messages may be routed to different Slack channels by error level. The
`webhook_default` setting is used as fallback.  You can also map specific
tasks to dedicated channels using the `task_channels` dictionary in the
`slack` section.  Unmatched tasks fall back to the level-based routing or
`webhook_default`.

Example:

```yaml
slack:
    webhook_default: https://hooks.slack.com/services/XXX/YYY/ZZZ
    task_channels:
        backup: https://hooks.slack.com/services/AAA/BBB/CCC
        deploy: https://hooks.slack.com/services/DDD/EEE/FFF
```

# Message format and validation

Each hume message includes a `version` field that indicates the payload
format. The daemon validates every incoming packet, checking the version
and required fields before accepting it. Messages that fail validation are
ignored to prevent malformed data from being stored.

# Implementation, concepts, ideas

## Ideas for implementation

hume uses zeromq over loopback to connecto to a hume daemon on the same
server. It must reduce its footprint as much as possible, we dont want hume
to slow down other processes. I am testing zmq-ipc and zmq-tcp, as well as
PUSH/PULL and REQ/REP scenarios. A systemd unit file is included for the hume
daemon (humed). A pid file will be read and checked by the hume client to
know beforehand if the hume daemon is working. A watchdog script that
triggers a special hume mode should exist to report working status. A lack
of watchdog-pinging will help the devops team detect the situation quickly.

The hume daemon will filter/store the hume packets, and send them to the
main repository which will be a relational database coupled with redis for
current-data storage and querying.

## Weird future concepts

* Signed script verification (imagine, the script is created, signed, hume
checks the signature and executes/notifies if signature does not verify)

* Of course, authentication and authorization will need to be implemented.

* task templates: imagine this: 'hume template get wordpress_backup': You
get a wordpress_backup bash script that's only the required hume tasknames,
required informational stages.  All comments.  You just write the script to
follow the devops pattern.

* watchdog command: 'This task needs to run daily' -> cron failed? hume
command that lets the watchdog know it is effectively running daily.

* A publisher/subscriber subsystem?

Maybe one wants to propagate an event.

Maybe we want to set some value for others to consume (this could be related to Prometheus idea below)

* Prometheus compatibility

Humed should maintain the last status regarding a particular host:task
(humed might end up receiving information from more than one host, specially
in containerized environments?).

That data is valid for a time series based scraper such as Prometheus.

An in-memory db should work in this scenario, with possibly a persistent option.

KEY = host:task?
VALUES = All of HumePkt? timestamp included.

The MSG might not end up being graphed... :P but Grafana for instance supports
Text panels. It might be nice to be able to design a Hume Tasks dashboard.

`humed` exposes a simple HTTP endpoint at `/metrics` which provides
Prometheus-formatted statistics.  When the optional `token` setting is
defined under the `metrics` section of the configuration, requests must
include an `Authorization` header with the value `Bearer <token>` in order
to retrieve the metrics.

The daemon can also require an authentication token from `hume` clients. Set
`auth_token` at the top level of `humed`'s configuration and pass the same value
using the `--auth-token` option (or `HUME_TOKEN` environment variable) when
invoking `hume`.

* mailx drop-in replacement

unattended-upgrades and other packages send mail notifications using mailx. Write
a hume-mailx that can be used as alternative.

# Components

## hume

called from within scripts.  writes to a local publish queue.  maybe a
fallback to sqlite that humed can read on startup?

## humed

its the local publish queue.  consumes messages, applies
filtering/preprocessing, security, etc.  Can be set to primary or secondary mode. 
This way the hume CLI tool will just push gather some info, then push zmq
messages to localhost humed.  if localhost humed is a secondary, it will have a
thread to send pending hume messages to the primary.  query tool should work
against secondary or primary.

## Transfer Methods

Humed currently supports slack, logstash, syslog and remote syslog.

Next feature is multiple transfers, and this will require a bit of
refactoring, plus a threaded model.

In the future it will probably support fluentd and kant (our own query
database / tool / dashboard system).

Development will continue with logstash, then kant and finally fluentd,
because I am not finding good fluent client/agent implementations in
python3.

The logstash support uses python-logstash-async.


# DEVELOPMENT NOTES

## Define Basic CLI usage
* register and start process execution
* add events to process --warn, --info, --error, --debug
* event flagging for process timeline (instead of starting/stopping the watch, as every event including start/stop of process will include timestamp, we use event flagging to indicate events in the process timeline)
* stop process / deregister

## Miscelaneous
* mention export LINENO before calling hume

## Watchdog

`humewatchdog.py` can be used to monitor that the `humed` daemon is alive.
It checks the daemon's pidfile and optionally executes a command when the
process disappears.  The script may run once or periodically using the
``--interval`` option:

```
$ python3 humewatchdog.py --interval 60 --alert-cmd 'systemctl restart humed'
```

When ``--interval`` is provided the watchdog will continue checking every
specified number of seconds.

## TODO
* Make humeconfig's --from-url work
* add support to managing issues from within hume, example:

```
~$ humeconfig --update --github $GITHUB_TOKEN
Github Token configured.
Config file updated.

~$ hume --beer --deliver-to=buanzo
hume: No such command

~$ hume --task hume --level critical --open-issue "Hume support for beer brewing"
Github Issue #45 created: github.com/hume/issues/45
  
[ some days later ]

~$ hume --beer --deliver-to=buanzo --verbose
OK
~$ hume --task hume --level ok --fix-issue 45
Github Issue #45 fixed and closed
```
