-- Runs once, when the data volume is first created.
--
-- The test suite truncates tables between cases. It therefore needs a database
-- of its own: pointed at the development database, a single `pytest` run would
-- delete whatever you were working with.
CREATE DATABASE banking_test OWNER banking;
