import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def main():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL is missing from environment variables.")
        return

    print("Connecting to Supabase PostgreSQL database...")
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Ensure users table has auth_token text column
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_token text;")
        print("✓ Checked/Added auth_token column to 'users' table")

        # Drop existing tables if they exist
        cursor.execute("DROP TABLE IF EXISTS deal_payment_milestones CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS brand_deals CASCADE;")
        
        # Create brand_deals table
        cursor.execute("""
            CREATE TABLE brand_deals (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                creator_id text NOT NULL,
                brand_name text NOT NULL,
                deliverables text NOT NULL,
                rate_amount numeric NOT NULL,
                currency text DEFAULT 'INR',
                usage_rights text,
                exclusivity_clause text,
                timeline_start timestamp with time zone,
                timeline_end timestamp with time zone,
                status text DEFAULT 'active',
                contract_pdf text,
                cover_note_type text DEFAULT 'english',
                created_at timestamp with time zone DEFAULT now()
            );
        """)
        print("✓ Created table 'brand_deals'")

        # Create deal_payment_milestones table
        cursor.execute("""
            CREATE TABLE deal_payment_milestones (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                deal_id bigint REFERENCES brand_deals(id) ON DELETE CASCADE,
                milestone_name text NOT NULL,
                amount numeric NOT NULL,
                due_date timestamp with time zone NOT NULL,
                paid_status text DEFAULT 'unpaid',
                reminder_sent_at timestamp with time zone,
                created_at timestamp with time zone DEFAULT now()
            );
        """)
        print("✓ Created table 'deal_payment_milestones'")

        # Create analytics_events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_events (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                user_id text,
                event_name text NOT NULL,
                timestamp timestamp with time zone DEFAULT now()
            );
        """)
        print("✓ Checked/Created table 'analytics_events'")

        # Create creator_feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_feedback (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                creator_id text,
                deal_id bigint,
                rating text,
                comment text,
                created_at timestamp with time zone DEFAULT now()
            );
        """)
        print("✓ Checked/Created table 'creator_feedback'")

        # Enable RLS
        print("Enabling Row Level Security (RLS)...")
        cursor.execute("ALTER TABLE brand_deals ENABLE ROW LEVEL SECURITY;")
        cursor.execute("ALTER TABLE deal_payment_milestones ENABLE ROW LEVEL SECURITY;")
        cursor.execute("ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;")
        cursor.execute("ALTER TABLE creator_feedback ENABLE ROW LEVEL SECURITY;")
        print("✓ Enabled RLS on brand_deals, deal_payment_milestones, analytics_events, and creator_feedback")

        # Create Policies
        print("Creating RLS policies...")
        cursor.execute("""
            CREATE POLICY brand_deals_owner_policy ON brand_deals
            FOR ALL USING (creator_id = auth.jwt() ->> 'email');
        """)
        
        cursor.execute("""
            CREATE POLICY milestones_owner_policy ON deal_payment_milestones
            FOR ALL USING (
                EXISTS (
                    SELECT 1 FROM brand_deals
                    WHERE brand_deals.id = deal_payment_milestones.deal_id
                    AND brand_deals.creator_id = auth.jwt() ->> 'email'
                )
            );
        """)

        cursor.execute("""
            CREATE POLICY insert_analytics_policy ON analytics_events
            FOR INSERT WITH CHECK (user_id = auth.jwt() ->> 'email');
        """)

        cursor.execute("""
            CREATE POLICY select_analytics_policy ON analytics_events
            FOR SELECT USING (user_id = auth.jwt() ->> 'email');
        """)

        cursor.execute("""
            CREATE POLICY insert_feedback_policy ON creator_feedback
            FOR INSERT WITH CHECK (creator_id = auth.jwt() ->> 'email');
        """)

        cursor.execute("""
            CREATE POLICY select_feedback_policy ON creator_feedback
            FOR SELECT USING (creator_id = auth.jwt() ->> 'email');
        """)
        print("✓ Applied owner policies for creator_id / user_id matching auth.jwt() ->> 'email'")

        cursor.close()
        conn.close()
        print("Database setup complete and successful!")
        
    except Exception as e:
        print(f"Failed to setup database tables: {e}")

if __name__ == "__main__":
    main()
