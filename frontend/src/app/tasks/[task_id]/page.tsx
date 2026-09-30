import { TaskDetailClient } from './TaskDetailClient';

interface Props {
  params: Promise<{ task_id: string }>;
}

// Next.js 15: params is a Promise
export default async function TaskDetailPage({ params }: Props) {
  const { task_id } = await params;
  return <TaskDetailClient taskId={task_id} />;
}
