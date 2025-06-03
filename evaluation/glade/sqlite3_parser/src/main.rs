use sqlparser::parser::Parser;
use sqlparser::dialect::SQLiteDialect;
use std::process;

fn main() {
    let sql = "SELECT * FROM users";
    let dialect = SQLiteDialect {};
    let cmd = Parser::parse_sql(&dialect, sql);
    if let Err(e) = cmd {
        process::exit(1);
    }
    process::exit(0);
}
