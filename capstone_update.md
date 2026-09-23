# Capstone Update

One technical challenge was making repeated incidents at the same site visible on the map. Several events share identical latitude and longitude values, so the dashboard applies a small random jitter to each plotted point. This preserves the correct site area while making overlapping incidents easier to inspect.

I also separated lagging indicators, such as total incidents, TRIR, and LTIF, from leading indicators, such as near-miss reporting, inspection completion, training compliance, and critical control pass rate. That distinction helped the dashboard move from only explaining what happened to showing where risk is building now.
