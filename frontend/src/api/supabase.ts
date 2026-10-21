import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 
  import.meta.env.VITE_SUPABASE_URL || 
  import.meta.env.NEXT_PUBLIC_SUPABASE_URL || 
  'https://owqfygxtgntyyzdcospe.supabase.co';

const supabaseAnonKey = 
  import.meta.env.VITE_SUPABASE_ANON_KEY || 
  import.meta.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || 
  'sb_publishable_A1cCnAAzB9zh4b_KJmQVog_V5EeU163';

export const isSupabaseConfigured = () => {
  return Boolean(supabaseUrl && supabaseAnonKey);
};

export const supabase = isSupabaseConfigured()
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

/**
 * Subscribes to live repair-job status changes via Supabase Realtime
 */
export const subscribeToRepairJobs = (onUpdate: (payload: any) => void) => {
  if (!supabase) return () => {};

  const channel = supabase
    .channel('phoenix-realtime-repairs')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'repair_jobs' },
      (payload) => {
        onUpdate(payload);
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
};

/**
 * Subscribes to live incident changes via Supabase Realtime
 */
export const subscribeToIncidents = (onUpdate: (payload: any) => void) => {
  if (!supabase) return () => {};

  const channel = supabase
    .channel('phoenix-realtime-incidents')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'incidents' },
      (payload) => {
        onUpdate(payload);
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
};
