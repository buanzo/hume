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
          "text": "*Hostname:*\n{{ hostname }}"
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
    {
        "type": "divider"
    },
  ]
}