#!/usr/bin/env python3
import os
import re
import sys
from glob import glob
import argparse
from pprint import pprint
from jinja2 import FileSystemLoader, Environment, TemplateNotFound, FunctionLoader
from collections import OrderedDict


class HumeRenderer():
    def __init__(self,templates_dir=None, transfer_method=None, debug=False):
        self.debug = debug

        if templates_dir is None:
            raise(ValueError('templates_dir must be passed to HumeRenderer'))
        if transfer_method is None:
            raise(ValueError('transfer_method must be passed to HumeRenderer'))

        if self.debug:
            printerr('HumeRenderer: templates_dir="{}"'.format(templates_dir))
            printerr('HumeRenderer: transfer_method="{}"'.format(transfer_method))

        self.transfer_method = transfer_method
        # Setup jinja using templates_dir
        # TODO: Check Exceptions for FileSystemLoader and implement try/except
        self.tplDir = '{}/{}'.format(templates_dir, transfer_method)
        loader = FileSystemLoader(self.tplDir)
        if self.debug:
            printerr('HumeRenderer: Using tplDir = "{}"'.format(self.tplDir))
        self.jinja2 = Environment(loader=loader,
                                  trim_blocks=True)  # TODO: check need of trim
        # Configure an internal loader using a callback function.
        # useful when no template files are available, prolly broken humed install
        internal = FunctionLoader(self.internal_tpl_loader)
        self.jinja2fallback = Environment(loader=internal,
                                          trim_blocks=True)

    def internal_tpl_loader(self,name):
        if name == 'slack':  # One default template per transfer method:
            return('''
{
   "blocks": [
    {
        "type": "divider"
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Priority Level:* {{ hume.level }}\n{{ hume.msg }}"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Sender:*\n{{ hume.hostname }} via {{ humed.hostname }}"
        },
        {
          "type": "mrkdwn",
          "text": "*Task:*\n{{ hume.task }}"
        },
        {
          "type": "mrkdwn",
          "text": "*Timestamp*\n{{ hume.timestamp }}"
        },
        {
          "type": "mrkdwn",
          "text": "*Tags:*\n{% for tag in hume.tags %}{{ '#' + tag  + ' '}}{% endfor %}"
        }
      ]
    },
{% if hume.extra.items()|count > 0 %}
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Extra fields:*\n"
      },
      "fields": [
      {% for key, value in hume.extra.items() %}
        {
          "type": "mrkdwn",
          "text": "*{{ key }}:*\n{{ value }}"
        },
      {% endfor %}
      ]
    },
{% endif %}
    {
        "type": "divider"
    },
  ]
}
''')
        else:
            return('No fallback template for method="{}"'.format(name))

    def available_bases(self):
        # This method returns base name tpl files in templates_dir
        # By BASE we means those named NAME_default.tpl
        # i.e we return a list of NAMEs
        ret = []
        tpls = glob('{}/*_default.tpl'.format(self.tplDir), recursive=False)
        for item in tpls:
            ret.append(os.path.basename(item).split('_default.tpl')[0])
        return(ret)

    def render(self,base_template=None, level='info', humed_hostname=None, humePkt=None):
        # This function gets the template file for the base, according
        # to selection process:
        # priority -> default -> method default -> ERROR
        # That means: if user chooses slack as transport, "example"
        # as base, and the priority is 'critical', will return
        # whatever is available in this order:
        # {tpldir}/example_critical.tpl
        # {tpldir}/example_default.tpl
        # {tpldir}/default_default.tpl
        # ERROR
        # Default level is info, we can get it from humePkt but...
        # no need to re-execute
        if base_template is None:
            raise(ValueError('render: base_template needs to be specified'))
        if humePkt is None:
            raise(ValueError('render: humePkt object must be passed'))
        if humed_hostname is None:
            raose(ValueError('render: humed_hostname is missing'))
        # Let's try to render according to availability
        # TODO: use packageloader for hume-provided templates
        # TODO: better yet, also use ChoiceLoader
        # https://jinja.palletsprojects.com/en/2.11.x/api/#loaders
        options = []
        options.append('{}_{}.tpl'.format(base_template, level))
        options.append('{}_default.tpl'.format(base_template))
        options.append('default_{}.tpl'.format(level))
        options.append('default_default.tpl')

        # base_template might be 'default'. I prefer this to avoid dups:
        options = list(OrderedDict.fromkeys(options))


        # Build renderContext
        renderContext = {'hume': {}, 'humed': {}}
        for key, val in humePkt['hume'].items():
            renderContext['hume'][key] = val
        renderContext['humed']['hostname'] = humed_hostname
        # Try each template option in order of priority. Return ASAP.
        # If no template option exists, use another loader
        for option in options:
            r = None
            if self.debug:
                printerr('HumeRenderer: Trying option = "{}"'.format(option))
            try:
                r = self.jinja2.get_template(option).render(renderContext)
            except TemplateNotFound:
                continue
            except Exception as exc:
                printerr('Exception: {}'.format(exc))
                continue
            else:
                break
        if r is None:  # No template worked, use internal fallback loader
            if self.debug:
                printerr('HumeRenderer: Fallback for "{}"'.format(self.transfer_method))
            r = self.jinja2fallback.get_template(self.transfer_method).render(renderContext)
        return(r)

class NotImplementedAction(argparse.Action):
    """ This class allows to work on getting your Argparse object
    ready even if nothing useful happens when used.

    Usage:
    Just set action=NotImplementedAction when calling add_argument, like this:

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing",
                        help="This will do something in the future",
                        action=NotImplementedAction)

    GIST URL: https://gist.github.com/buanzo/2a004348340ef79b0139ab38f719cf1e
    """
    def __call__(self, parser, namespace, values, option_string=None):
        msg = 'Argument "{}" still not implemented.'.format(option_string)
        sys.exit(msg)


# Guess.
def printerr(msg):
    print("{}".format(msg), file=sys.stderr)


def pprinterr(o):
    pprint(o, stream=sys.stderr)


def valueOrDefault(o, k, d):
    # This function tries to find a key
    # or an attribute named k.
    # If it finds either, it returns d.
    if isinstance(o, dict):
        if k in o.keys():
            return(o[k])
    try:
        r = getattr(o, k)
    except AttributeError:
        return(d)
    return(r)


def envOrDefault(v, d):
    # return the contents of an env var 'v'
    # or default d.
    ov = os.environ.get(v)
    if ov is None:
        return(d)
    else:
        return(str(ov).strip())


def is_valid_hostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))
