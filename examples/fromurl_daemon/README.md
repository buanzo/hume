# From-Url Daemon Example

humeconfig supports a --from-url switch which, along optional
--digitalocean, enables dynamic configuration provisioning.

This folder contains an example for an http server. Why not https? its up
to you to proxy and firewall this appropriately.

The only functionality I want to show here is how from-url should work,
and how it can be implemented in various scenarios, such as with
--digitalocean [What to check for, authn/authz, etc]
