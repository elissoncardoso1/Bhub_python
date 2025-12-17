'use client';

import { ArticleDetailPage } from '@/pages/ArticleDetailPage';
import { useParams } from 'next/navigation';

export default function ArticleDetail() {
  const params = useParams();
  const id = params?.id as string | undefined;
  
  return <ArticleDetailPage articleId={id} />;
}
