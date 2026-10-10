// ORD-0572: merged back by LocaleContext in lexicographic domain-file order.
import { agent } from "./agent";
import { auth } from "./auth";
import { bookings } from "./bookings";
import { calendar } from "./calendar";
import { checkin } from "./checkin";
import { detail } from "./detail";
import { discovery } from "./discovery";
import { exec } from "./exec";
import { fmt } from "./fmt";
import { hub } from "./hub";
import { inbox } from "./inbox";
import { intel } from "./intel";
import { itinerary } from "./itinerary";
import { lib } from "./lib";
import { live } from "./live";
import { main } from "./main";
import { map } from "./map";
import { mapComp } from "./mapComp";
import { me } from "./me";
import { member } from "./member";
import { mobile } from "./mobile";
import { mobility } from "./mobility";
import { my } from "./my";
import { nav } from "./nav";
import { offline } from "./offline";
import { pending } from "./pending";
import { planai } from "./planai";
import { planning } from "./planning";
import { poiImport } from "./poiImport";
import { poster } from "./poster";
import { push } from "./push";
import { recovery } from "./recovery";
import { setup } from "./setup";
import { shared } from "./shared";
import { sharedPoster } from "./sharedPoster";
import { shell } from "./shell";
import { simulation } from "./simulation";
import { spend } from "./spend";
import { stay } from "./stay";
import { studio } from "./studio";
import { today } from "./today";
import { trial } from "./trial";
import { twin } from "./twin";
import { v14 } from "./v14";
import { v8panelregistry } from "./v8panelregistry";

export const domainBooks: { en: Record<string, string>; zh: Record<string, string> }[] = [
  agent,
  auth,
  bookings,
  calendar,
  checkin,
  detail,
  discovery,
  exec,
  fmt,
  hub,
  inbox,
  intel,
  itinerary,
  lib,
  live,
  main,
  map,
  mapComp,
  me,
  member,
  mobile,
  mobility,
  my,
  nav,
  offline,
  pending,
  planai,
  planning,
  poiImport,
  poster,
  push,
  recovery,
  setup,
  shared,
  sharedPoster,
  shell,
  simulation,
  spend,
  stay,
  studio,
  today,
  trial,
  twin,
  v14,
  v8panelregistry,
];
