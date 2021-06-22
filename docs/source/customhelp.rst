A Customisable Custom Help Cog For Red:
=======================================


| Couldn't get a shorter title. Anyways, the cog introduces categories,meaning you can now bunch up cogs into one blob and give it a name,description and reaction.
|
| This cog is made cause I didn't like 30 help pages for my bot and i wanted to bunch my cogs.
|
| Use ``[p]chelp`` to see what can be customised and ``[p]chelp settings`` for even more customisations.
| 
| Oh and as an additional bonus, If you have the alias cog loaded. those alias's help can also be retrieved. 

Setup
-------
*Note: Use* ``[p]chelp set 1`` *to set your help to the custom help, else it'll remain as the normal one* 

1. | Start by doing ``[p]chelp list`` to list all your cogs

2. | Pick the cogs you need to group into a category.
   | Then use ``[p]chelp create`` , now add the catergorized cogs as shown below.

   .. note::
    This command can be run as many times as needed and can load up cogs into existing categories as well.

   | This is the yaml syntax.

   .. code:: yaml

      category1:
       - Cog1
       - Cog2
      category2:
       - Cog3
       - Cog4
   
   | |create categories|

3. Congrats you just bunched up cogs into categories. Now you can do
   ``[p]help <category>`` to load the help of all those cogs in the category.

4. | Now ``[p]chelp list`` should show the categories made and your help must look cooler! 
   | |raw help|
   
5. | Yay! *but wait* , we need to fill in the blanks
   | Use ``[p]chelp edit`` to add the everything you need to customise a category. 
   | The format is simply:

   .. code:: yaml

      category:
      - name: new name (ONLY use this to rename! else this isn't necessary)
      - desc: new description
      - long_desc: long description
      - reaction: reaction emoji

   | you can mix and match, as much as you want. Like the example below
   | |editz|

6. | Now the main help menu must look a little better.
   | |Default command|

7.  *but wait, there's more.*

Themes
-------

Introducing themes that were shamesslessly ripped off from other bots cause I'm bad at designing. 

1. | ``[p]chelp listthemes`` to get all the themes and the features available in each of them.
   | |list themes|

2. ``[p]chelp load <theme> feature`` to load the respective stuff.
   
   .. note::
      | You can use ``[p]chelp load <theme> all`` to load all the available feature in that theme.
      | You can mix and match any theme. (you won't lose ur categories <_<)

   | An example of ``[p]chelp load dank main`` is shown below
   | |image5| 

3. | ``[p]chelp show`` to show what themes are loaded.
   | |image6|
     
4. ``[p]chelp unload feature`` to reset the given feature back to default

5. ``[p]chelp reset`` to reset everything back to the default custom help
   
.. note:: 
    This won't revert to the previous red help, to do so use ``[p]chelp set 0``

6. wew, wait you thought we are done? *or are we*

More configurablity
--------------------

1. ``[p]chelp dev`` to add categories that can only be visible by the owner.
   
2. ``[p]chelp nsfw`` to add categories that can only be visible in nsfw channels.
   
3. ``[p]chelp auto`` to automatically make categories for you based on the tags in cogs!.
   
4. ``[p]chelp info`` to see a brief description of categories.
   
5. | Custom Arrows, YAY!
   | If you feel the default arrow icons are boring and plain, this is what you probably need (Supports emotes ofc).
   | You can also use plain emoji ids, The format is
   
   .. code-block:: javascript

      left : emoji
      right: emoji
      cross: emoji
      home : emoji
      force_left: emoji
      force_right: emoji

Additional Notes
-----------------

-  Don't be a moron trying to mix minimal theme (non-embed) with the other embed-based themes.

-  Use `[p]helpset pagecharlimit` to increase or decrease your page size, so as to add/subract more categories per page.

-  For my sanity, kindly disable menus if you are using the minimal theme.

-  A **Good Practice** is to have the category names all **lowercased** and the category description as **Camelcase**.
  
-  All the reactions and arrow emojis can be **custom** and even **animated**, You can even put the emoji ID (if u don't have nitro).
  
-  | Free to tell about new themes which you might want to see. Let me know if you think any part of the theme can be made better.
   | I'm available in the `cog support server <https://discord.gg/GET4DVk>`__.

-  If the owner of any bot feels that their theme needs to be removed from this cog. Please inform me, I'll remove it.

FAQ
----

1. Reactions are not working, why?!

   1. Your bot should have the react perms
   2. ``[p]helpset usemenus 1`` (menus must be enabled)

2. Can I make my own theme in your cog?
    
   | Well you can just learn about the help formatter api.
   | If u really need categories as well then you can fork my repo,
     navigate to the themes folder, see how the themes are made and make a
     new file in that folder with your custom coded theme and load the cog. 
   | your theme should magically occur in the ``[p]chelp listthemes``

3. Some of my reactions are vanishing?

   You are probably having more than 14 categories. A message can only have 14 reactions from a bot at max (I think).
   This is a discord limitation and it's unhandled by the cog.

Credits
--------
-  My heartfelt thanks to `OofChair <https://github.com/OofChair>`__ and `TwinShadow <https://github.com/TwinDragon>`__.
   Both of these amazing people did some major testing and contribution to the cog.
-  To everyone who patiently answered my noob coding questions.
-  To the other bots ``R.Danny``, ``Dankmemer``, ``Nadeko`` from which the theme designs were taken.
-  ``Pikachu's help menu`` from `Flare <https://github.com/flaree/>`__
   which was the spark, that the idea of this cog isn't too far fetched
-  The whole Red community cause redbot is epic and the help\_formatter
   is God sent.
-  Special thanks to `Jackenmen <https://github.com/jack1142>`__ who
   solved most of the doubts that came during the development.

.. |create categories| image:: images/chelp_create.png
.. |raw help| image:: images/raw_help.png
   :width: 300
.. |editz| image:: images/edits.png
   :width: 400
.. |Default command| image::  images/final_help.png
   :width: 400
.. |list themes| image:: images/listthemes.png
.. |image5| image:: images/myhelp.png
.. |image6| image:: images/chelp_show.png
