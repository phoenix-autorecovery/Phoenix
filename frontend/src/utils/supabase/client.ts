import { createBrowserClient } from '@supabase/ssr';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || import.meta.env.NEXT_PUBLIC_SUPABASE_URL || 'https://owqfygxtgntyyzdcospe.supabase.co';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_A1cCnAAzB9zh4b_KJmQVog_V5EeU163';

export const createClient = () => {
  return createBrowserClient(
    supabaseUrl,
    supabaseKey
  );
};
