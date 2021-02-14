# A Customisable Custom Help Cog For Red: (This is a BETA cog)
Couldn't get a shorter title. Anyways, the cog introduces categories, meaning you can now bunch up cogs into one blob and give it a name, description and reaction.  
Use `[p]chelp` to see what can be customised.
Oh and as an additional bonus. If you have the alias cog loaded. those alias's help can also be retrieved.
## Setup:
*Note: Use `[p]chelp set 1` to set your help to the custom help, else it'll remain as the normal one*
1. Start by doing `[p]chelp list` to list all your cogs
![list categories](https://i.imgur.com/tsn6Rnx.png=30x5)  
2. Pick the cogs you need to group into a category. Then use `[p]chelp create`, now add the catergorized cogs as shown below. This is yaml syntax.  
Note:This command can be run as many times as needed and can load up cogs into existing categories as well.  
![create categories](https://imgur.com/8XDvrHH.png=30x5)  
3. Congrats you just bunched up cogs into categories. Now you can do `[p]help <category>` to load the help of all those cogs in the category. 
4. Now `[p]chelp list` should show the categories made yay! *but wait*
5. Well `[p]help` has many incompletes now.  
Use `[p]chelp edit` to add the everything you need to customise a category. 
The format is simply:  
```yaml
category:
 - name: new name (ONLY use this to rename! else this isn't necessary)
 - desc: new description
 - long_desc: long description
 - reaction: reaction emoji
```
you can mix and match, as much as you want. Like the example below  
![editz](https://imgur.com/m4LtUy4.png)  
6. Now the main help menu must look a little better.  
![Default command](https://imgur.com/72GXRY8.png)  
7. *butt weight there's more.*  

## Themes:
Introducing themes that were shamesslessly ripped off from other bots cause I'm bad at designing.
1. `[p]chelp listthemes` to get all the themes and the features available in each of them.  
![](https://imgur.com/m83FC1N.png)
2. `[p]chelp load <theme> feature` to load the respective stuff.  
*Note: you can use `[p]chelp load <theme> all` to load all the available feature in that theme(sorry OofChair)*    
An example of `[p]chelp load dank main` is shown below  
![](https://imgur.com/Fr1SS37.png)
3. `[p]chelp show` to show what themes are loaded.  
![](https://imgur.com/tW7sFkX.png)
4. `[p]chelp unload feature` to reset the given feature back to default
5. `[p]chelp reset` to reset everything back to the default custom help  
*Note: This won't revert to the previous red help, to do so use `[p]chelp set 0`*
6. wew, wait you thought we are done? *or are we*

## More configurablity:
1. `[p]chelp dev` to add categories that can only be visible by the owner.
2. `[p]chelp nsfw` to add categories that can only be visible in nsfw channels.
3. `[p]chelp auto` to automatically make categories for you based on the tags in cogs!.
4. `[p]chelp info` to see a brief description of categories.

## Additional Notes:
- A **Good Practice** is to have the category names all **lowercased** and the category description as **Camelcase**.
- All the reactions and arrow emojis can be custom and even animated.
- Free to tell about new themes which you might want to see. Let me know if you think any part of the theme can be made better. I'm available in the [cog support server]( https://discord.gg/GET4DVk).
- If the owner of any bot feels that their theme needs to be removed from this cog. Please inform me, I'll remove it.  
## FAQ:
1. Reactions are not working, why?!  
	1. Your bot should have the react perms
	2. `[p]helpset usemenus 1` (menus must be enabled)
2. Can I make my own theme in your cog?  
	Well you can just learn about the help formatter api.  
	If u really need categories as well then you can fork my repo, navigate to the themes folder, see how the themes are made and make a new file in that folder with your custom coded theme and load the cog. your theme should magically occur in the `[p]chelp listthemes`  
## Credits:
- My heartfelt thanks to [OofChair](https://github.com/OofChair) and [TwinShadow](https://github.com/TwinDragon). Both of these amazing people did some major testing and contribution to the cog.
- To everyone who patiently answered my noob coding questions.
- To the other bots `R.Danny`,`Dankmemer`, `Nadeko` from which I got inspiration.
- `Pikachu's help menu` from [Flare](https://github.com/flaree/) which is the base help design of this cog (This isn't available anymore, cause flare requested it's removal).
- The whole Red community cause redbot is epic and the help_formatter is God sent.
- Special thanks to [Jackenmen](https://github.com/jack1142) who solved most of the doubts that came during the development.
