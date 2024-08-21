import os
import time
import inspect
import sqlite3


class CmbProfileConnection(sqlite3.Connection):
    def __init__(self, path, **kwargs):
        super().__init__(path, **kwargs)

        self.executescript(
            """
            CREATE TABLE IF NOT EXISTS __profile__ (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                plan TEXT,
                executions INTEGER NOT NULL DEFAULT 1,
                total_time INTEGER NOT NULL DEFAULT 0,
                average_time INTEGER NOT NULL DEFAULT 0,
                min_time INTEGER NOT NULL DEFAULT 0,
                max_time INTEGER NOT NULL DEFAULT 0,
                callers JSONB
            );
            """
        )

        # Striped querys PK dictionary
        self._querys = {}

        # Populate querys
        for row in super().execute("SELECT id, query FROM __profile__;"):
            id, query = row
            self._querys[query] = id

    def cursor(self):
        return super(CmbProfileConnection, self).cursor(CmbProfileCursor)

    def execute(self, *args):
        start = time.monotonic_ns()
        retval = super().execute(*args)
        self.log_query(time.monotonic_ns() - start, *args)
        return retval

    def log_query(self, exec_time, *args):
        query = args[0].strip()

        if query.startswith("CREATE") or query.startswith("PRAGMA"):
            return

        caller = inspect.getframeinfo(inspect.stack()[2][0])
        file = os.path.basename(caller.filename).removesuffix('.py')
        function = caller.function
        # Use a different dot to avoid json syntax error
        caller_id = f"{file}․{function}:{caller.lineno}"

        if file == "cmb_db" and function == "execute":
            caller = inspect.getframeinfo(inspect.stack()[3][0])
            file = os.path.basename(caller.filename).removesuffix('.py')
            caller_id = f"{file}․{caller.function}:{caller.lineno} {caller_id}"

        # Convert from nano seconds to micro seconds
        exec_time = int(exec_time / 1000)
        pk_id = self._querys.get(query, None)

        if pk_id is None:
            # Get query plan
            if len(args) > 1:
                c = super().execute(f"EXPLAIN QUERY PLAN {query}", args[1])
            else:
                c = super().execute(f"EXPLAIN QUERY PLAN {query}")

            # Convert plan to a string
            plan = []
            for row in c:
                plan.append(" ".join(str(row)))
            plan = "\n".join(plan)

            # Create new query entry in profile table
            c = super().execute(
                """
                INSERT INTO __profile__(query, plan, total_time, average_time, min_time, max_time, callers)
                VALUES(?, ?, ?, ?, ?, ?, json(?))
                RETURNING id;
                """,
                (query, plan, exec_time, exec_time, exec_time, exec_time, f"""{{"{caller_id}": 1}}""")
            )
            pk_id = c.fetchone()[0]
            self._querys[query] = pk_id
        else:
            # Increment number of executions of this query
            super().execute(
                f"""
                UPDATE __profile__
                SET
                    executions=executions+1,
                    total_time=total_time+?,
                    average_time=total_time/executions,
                    min_time=min(min_time, ?),
                    max_time=max(max_time, ?),
                    callers=json_set(callers, '$.{caller_id}', callers->'$.{caller_id}' + 1)
                WHERE id=?;
                """,
                (exec_time, exec_time, exec_time, pk_id)
            )


class CmbProfileCursor(sqlite3.Cursor):
    def execute(self, *args):
        start = time.monotonic_ns()
        retval = super().execute(*args)
        self.connection.log_query(time.monotonic_ns() - start, *args)
        return retval
