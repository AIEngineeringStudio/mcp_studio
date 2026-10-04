**Color codes for Mermaid theme configuration**

|  # | Hex Code  | Descriptive Color  | Used For                                              |
|---:|-----------|--------------------|-------------------------------------------------------|
|  1 | `#ffffff` | White              | Background, primary fill, sequence number             |
|  2 | `#111827` | Very dark gray     | Line, primary text, actor text, label text, note text |
|  3 | `#374151` | Dark gray          | Primary border, activation border                     |
|  4 | `#98FB98` | Pale green         | Actor background                                      |
|  5 | `#009E60` | Shamrock green     | Actor border, signal text                             |
|  6 | `#6b7280` | Medium gray        | Actor line                                            |
|  7 | `#DE3163` | Deep pink / cerise | Signal                                                |
|  8 | `#EC5800` | Strong orange      | Label background, label border, loop text             |
|  9 | `#E4D00A` | Strong yellow      | Note background                                       |
| 10 | `#92400e` | Dark brown / amber | Note border                                           |
| 11 | `#e5e7eb` | Light gray         | Activation background                                 |

- `#ffffff`: White
- `#111827`: Very Dark Gray
- `#374151`: Dark Gray
- `#98FB98`: Pale Green
- `#6b7280`: Medium Gray
- `#DE3163`: Cerise
- `#00FFFF`: Cyan
- `#fef3c7`: Pale Amber
- `#92400e`: Dark Amber / Brown
- `#e5e7eb`: Light Gray

https://htmlcolorcodes.com/colors/shades-of-blue/  
https://htmlcolorcodes.com/colors/shades-of-red/  
https://htmlcolorcodes.com/colors/shades-of-green/  


> **Note:**  
> The main changes from the previous configuration are:  
> - `#009E60` for the actor border and signal text, 
> - `#EC5800` for labels/loop text, and 
> - `#E4D00A` for the note background.

---

%%{init: {"theme": "base", "themeVariables": {
"background": "#ffffff", "lineColor": "#111827", "textColor": "#ffffff", 
"primaryColor": "#ffffff", "primaryTextColor": "#111827", "primaryBorderColor": "#374151", 
"actorBkg": "#98FB98", "actorBorder": "#009E60", "actorTextColor": "#111827", "actorLineColor": "#6b7280", 
"signalColor": "#DE3163", "signalTextColor": "#009E60", 
"labelBoxBkgColor": "#EC5800", "labelBoxBorderColor": "#EC5800", "labelTextColor": "#111827", 
"loopTextColor": "#EC5800", 
"noteBkgColor": "#E4D00A", "noteBorderColor": "#92400e", "noteTextColor": "#111827", 
"activationBkgColor": "#e5e7eb", "activationBorderColor": "#374151", 
"sequenceNumberColor": "#ffffff"
}}}%%