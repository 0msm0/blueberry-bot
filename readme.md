### 16 June 2022 
v0.01 
- Basic bot with start command up and running which fetches fname lname username
- Wrote conversation handler to fetch wakeup time, first it asks hour range, then minute then comments.


### 18 June 2022 
v0.01 
Commands implemented -
- register - allowes user to register
- set_timezone - allows user to set_timezone (supports india us uk as of now)
- mytimezones - check previous timezones set
- wakesleep - add complete sleep+wakeup record in one conversation along with notes and save to database
- mywakesleeps - check previous sleep records, ordered by descending wakeup time (shows only 5 for now)


### IMP THINGS TO HANDLE
- Get user's location and set timezone - HANDLED by explicit set_timezone command
- TODO generalize all timezones (currently supports india us uk only)


### LEARNING
- Timeout is applicable to the entire conversation. 
- Timeout does not work properly for the nested conversation, definitely not for the inner conversation layer. Outer layer can have timeout, but it gets applied to inner automatically.
- So if you have give timeout for nested, give it to outer, and set it higher so that at each successive state has enough time to get completed and it does not run infinitely.

- map_to_parent important for nested otherwise the command won't run the second time