# Mileage Tracker Changes

This document is to plan out the changes needed for the mileage tracker. The scope of the mileage tracker is not for large travel expenses it is simply for ordinary trips using personal vehicles. The basis of these changes is to better align with chapter 5 of [IRS Pub 463](https://www.irs.gov/publications/p463?utm_source=chatgpt.com#en_US_2025_publink100034064). Chapter 5 provides a reference (not an official form) of a daily mileage tracker. 

- date
- destination
  - city
  - town
  - or area
- business purpose
- odometer start
- odometer stop
- miles for the trip
- expenses
- type
  - oil
  - gas
  - tolls
  - etc
- amount

I am modifying the mileage tracker to include a starting location and destination location. Since the destination may be multiple places, I want to account for multi-stop business trips. I am also renaming column explanation to business purpose for clarity.

I am also creating travel documents that will provide the user with the option to show attach documents showing the travel such as receipts, maps screenshots, etc.

## miles

1. Add column "starting_location"
2. Add column "destination_location"
3. Rename explanation to "business_purpose"

## miles_history

1. Add starting_location column
2. Add destination_location column
3. Rename explanation to business_purpose.

## travel_docs

1. Create table travel_docs
