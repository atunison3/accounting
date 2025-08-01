CREATE VIEW IF NOT EXISTS GeneralLedger AS 
SELECT
    l.ID,
    l.EntryID,
    j.Date,
    j.Description,
    l.AccountNumber,
    l.TransactionAmount,
    SUM(l.TransactionAmount) OVER (
        PARTITION BY l.AccountNumber
        ORDER BY j.Date, l.ID
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS RunningBalance
FROM Ledger l
JOIN Journal j ON j.ID = l.EntryID;

SELECT * 
FROM GeneralLedger
WHERE 
    AccountNumber = 111 AND 
    DATE >= '2010-03-01' AND 
    DATE <= '2010-03-07';


