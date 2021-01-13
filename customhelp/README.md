# A Customisable Custom Help Cog For Red 
Couldn't get a shorter title. Anyways, the cog introduces categories, meaning you can now bunch up cogs into one blob and give it a name, description and reaction.
All the commands are under `[p]chelp`

## Setup:
1. Start by doing `[p]chelp list` to list all your cogs
![list categories](https://i.imgur.com/tsn6Rnx.png=30x5)  
2. Pick the cogs you need to group into a category. Then use `[p]chelp create`, now add the catergorized cogs as shown below. This is yaml syntax.  
![create categories](https://imgur.com/8XDvrHH.png=30x5)  
Note:This command can be run as many times as needed and can load up cogs into existing categories as well.
3. Congrats you just bunched up cogs into categories. Now you can do `[p]help <category>` to load the help of all those cogs in the category. 
4. Now `[p]chelp list` should show the categories made yay! *but wait*
5. Well `[p]help` has many incompletes now. Use `[p]chelp add desc` and `[p]chelp add reaction` to add the description for the categories and reactions respectively. Like the example below  
![Adding description](https://imgur.com/ddAgIQe.png)
![Adding reaction](https://imgur.com/ieovfQv.png)
6. Now the main help menu must look a little better.  
![Default command](https://imgur.com/8Q35GoC.png)
7. *butt weight there's more.*

## Themes:
Introducing themes that were shamesslessly ripped off from other bots cause I'm bad at designing
1. `[p]chelp listthemes` to get all the themes and the features available in each of them.
2. `[p]chelp load <theme> feature` to load the respective stuff. an example of `[p]chelp load dank main` is shown below 
![](https://imgur.com/Fr1SS37.png)
3. `[p]chelp settings` to show what themes are loaded
4. `[p]chelp unload feature` to reset the given feature back to default
5. `[p]chelp resetall` to reset everything back to the default custom help
Note: This won't revert to the previous red help, to do so use `[p]chelp set 0`
## Additional Notes:
- Incase you don't like the word `uncategorised` as a category name and want to change it. Use `[p]chelp uncategory name <the name u want>`. the uncategory command has a few special gimmicks as well. example `[p]chelp uncategory desc <change the description>` and `[p]chelp uncategory reaction <new reaction>`
- A good practice is to have the category names all lowercased and the category description as camel case.

## Credits:
- To everyone who patiently answered my noob coding questions.
- To the other bots `R.Danny`,`Dankmemer` from which I got inspiration.
- `Pikachu's help menu` from [Flare](https://github.com/flaree/) which is the base help design of this cog (the layout).
- The whole Red community cause redbot is epic.
- Special thanks to [Jackenman](https://github.com/jack1142) who solved most of the doubts that came during the development.
