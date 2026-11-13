import { redirect } from 'next/navigation';

// The landing page now lives at the root. Keep old /welcome links working.
export default function Welcome() {
  redirect('/');
}
