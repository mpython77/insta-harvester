"""
Actions — write/mutation operations against Instagram.

This package is **opt-in**. Construct an :class:`InstaHarvest` with
``Settings.default()`` and accessing :attr:`InstaHarvest.actions` will
raise :class:`ConfigError` until you flip the actions config:

.. code-block:: python

    from dataclasses import replace
    from instaharvest import InstaHarvest, Settings

    settings = Settings.default()
    settings = replace(
        settings,
        actions=replace(settings.actions, enabled=True),
    )
    # ``dry_run`` is still True at this point — every call logs what
    # it would do and returns ActionStatus.DRY_RUN. Flip dry_run to
    # False once you have audited the call sites.

    with InstaHarvest(settings) as ih:
        result = ih.actions.social.follow("instagram")
        print(result.status, result.message)

The two-step opt-in is intentional. Instagram bans accounts for
abusive automation; this library does not pretend that risk away.

What lives here:

  * :class:`SocialActions`    — follow / unfollow
  * :class:`MessagingActions` — send_message
  * :class:`Actions`          — facade aggregating the above; this
                                is what :attr:`InstaHarvest.actions`
                                returns
"""

from instaharvest.actions.facade import Actions
from instaharvest.actions.messaging import MessagingActions
from instaharvest.actions.social import SocialActions

__all__ = ["Actions", "SocialActions", "MessagingActions"]
